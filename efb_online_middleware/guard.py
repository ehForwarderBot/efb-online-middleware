"""Opt-in robust PING/PONG middleware; legacy OnlineMiddleware remains unchanged."""
import json
import logging
import os
from pathlib import Path
import threading
import time

from ruamel.yaml import YAML
from ehforwarderbot import Middleware, coordinator, utils

LOG = logging.getLogger(__name__)


class GuardedMiddleware(Middleware):
    middleware_id = "online.GuardedMiddleware"
    middleware_name = "WeChat Online Guard (bounded worker)"
    __version__ = "0.1.0"

    def __init__(self, instance_id=None):
        super().__init__()
        p = utils.get_config_path(self.middleware_id)
        conf = YAML(typ="safe").load(p.read_text(encoding="utf-8")) if p.exists() else {}
        conf = conf or {}
        self.enabled = conf.get("enabled") is True
        self.echo_mp = str(conf.get("echo_mp") or "").strip()
        self.ping = str(conf.get("ping", "PING"))
        self.pong = str(conf.get("pong", "PONG"))
        self.interval = int(conf.get("interval", 1800))
        self.reply_timeout = int(conf.get("reply_timeout", 45))
        self.threshold = int(conf.get("failure_threshold", 3))
        self.notify_efb = conf.get("notify_via_efb") is True
        self.eat_pong = conf.get("eat_echo_msg", True) is True
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.reply = threading.Event()
        self.pending = False
        self.failures = 0
        self.state = "disabled"
        self.reason = "not_configured"
        self.last_ping = None
        self.last_pong = None
        self.status_file = Path(str(conf.get("status_file") or (p.parent / "status.json"))).expanduser()
        if self.enabled:
            if not self.echo_mp or not self.ping or not self.pong or self.ping == self.pong:
                raise ValueError("echo_mp, ping, pong required; ping and pong differ")
            if not 30 <= self.interval <= 86400 or not 5 <= self.reply_timeout <= 600:
                raise ValueError("interval or reply_timeout outside safe bounds")
            if not 1 <= self.threshold <= 20:
                raise ValueError("failure_threshold outside safe bounds")
            self.state, self.reason = "starting", "waiting_for_first_probe"
        self.save()
        if self.enabled:
            self.worker = threading.Thread(target=self.run, name="efb-online-guard", daemon=True)
            self.worker.start()
        else:
            LOG.info("Online guard disabled; no heartbeat traffic sent")

    def process_message(self, message):
        if not self.enabled:
            return message
        author = getattr(message, "author", None)
        if (getattr(author, "module_id", None) == "blueset.wechat"
                and getattr(author, "name", None) == self.echo_mp
                and getattr(message, "text", None) == self.pong):
            with self.lock:
                if self.pending:
                    self.last_pong = time.time()
                    self.reply.set()
                    return None if self.eat_pong else message
        return message

    def save(self):
        with self.lock:
            data = dict(version=1, profile=str(coordinator.profile),
                        enabled=self.enabled, state=self.state, reason=self.reason,
                        checked_at=time.time(), last_ping_at=self.last_ping,
                        last_pong_at=self.last_pong, interval=self.interval,
                        reply_timeout=self.reply_timeout, failure_threshold=self.threshold,
                        consecutive_failures=self.failures)
        p = self.status_file
        p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(p.parent, 0o700)
        tmp = p.with_name("." + p.name + "." + str(os.getpid()) + ".tmp")
        try:
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(data, f, sort_keys=True, ensure_ascii=False)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.chmod(tmp, 0o600)
            os.replace(tmp, p)
        finally:
            if tmp.exists():
                tmp.unlink()

    def notify(self, online):
        if not self.notify_efb:
            return
        try:
            master = coordinator.master
            for chat_id in master.config.get("admins", [])[:1]:
                master.bot_manager.send_message(
                    chat_id,
                    "微信在线探针恢复正常" if online else "微信在线探针连续失败，请检查")
        except Exception:
            LOG.exception("EFB alert failed; independent systemd monitor is separate")

    def update(self, ok, reason):
        with self.lock:
            old = self.state
            self.failures = 0 if ok else self.failures + 1
            self.state = ("online" if ok else "offline" if self.failures >= self.threshold
                          else "degraded")
            new, n = self.state, self.failures
            self.reason = reason
        self.save()
        if ok:
            LOG.info("WeChat PONG received (was %s)", old)
        else:
            LOG.warning("WeChat probe failed %s/%s: %s", n, self.threshold, reason)
        if new != old and (new == "offline" or new == "online" and old == "offline"):
            self.notify(new == "online")

    def probe(self):
        self.reply.clear()
        with self.lock:
            self.pending = True
            self.last_ping = time.time()
        self.save()
        ok, reason = False, "pong_timeout"
        try:
            slave = coordinator.slaves.get("blueset.wechat")
            bot = getattr(slave, "bot", None)
            if bot is None:
                reason = "wechat_bot_not_ready"
            else:
                mp = bot.mps().search(self.echo_mp)
                if len(mp) != 1:
                    reason = "echo_mp_not_unique_or_missing"
                else:
                    mp[0].send(self.ping)
                    ok = self.reply.wait(self.reply_timeout)
                    reason = "pong_received" if ok else "pong_timeout"
        except Exception as exc:
            reason = "probe_exception_" + type(exc).__name__
            LOG.warning("WeChat probe raised %s", type(exc).__name__)
        finally:
            with self.lock:
                self.pending = False
        self.update(ok, reason)

    def run(self):
        # Exactly one loop, no recursive schedulers or per-probe threads.
        while not self.stop.is_set():
            self.probe()
            if self.stop.wait(self.interval):
                break
