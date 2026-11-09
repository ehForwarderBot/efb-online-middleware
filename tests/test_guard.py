"""Unit tests for standalone state machine; never access production EFB."""
import json
import logging
import os
from pathlib import Path
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

from efb_online_middleware import guard as plugin


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.messages = []
        self.admin_notices = []
        self.coordinator = types.SimpleNamespace(
            profile="unittest", slaves={}, master=None)
        self.patcher = patch.object(plugin, "coordinator", self.coordinator)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.guard = plugin.GuardedMiddleware.__new__(plugin.GuardedMiddleware)
        g = self.guard
        g.enabled = True
        g.echo_mp = "Example Official Account"
        g.ping, g.pong = "PING", "PONG"
        g.interval, g.reply_timeout, g.threshold = 1800, 8, 3
        g.notify_efb = False
        g.eat_pong = True
        g.lock = threading.RLock()
        g.stop, g.reply = threading.Event(), threading.Event()
        g.pending, g.failures = False, 0
        g.state, g.reason = "starting", "waiting_for_first_probe"
        g.last_ping = None
        g.last_pong = None
        g.status_file = Path(self.temp.name) / "status.json"
        g.notify = lambda online: self.admin_notices.append(online)
        g.save()

    def message(self, text, name=None, module="blueset.wechat"):
        return types.SimpleNamespace(
            text=text,
            author=types.SimpleNamespace(
                module_id=module,
                name=name if name is not None else self.guard.echo_mp))

    def test_unrelated_messages_are_never_swallowed(self):
        g = self.guard
        g.pending = True
        for msg in (self.message("hello"), self.message("PONG", "Other account"),
                    self.message("PONG", module="blueset.telegram")):
            self.assertIs(g.process_message(msg), msg)
        self.assertFalse(g.reply.is_set())

    def test_only_active_matching_pong_is_swallowed(self):
        g = self.guard
        m = self.message("PONG")
        self.assertIs(g.process_message(m), m)
        g.pending = True
        self.assertIsNone(g.process_message(m))
        self.assertTrue(g.reply.is_set())
        self.assertIsNotNone(g.last_pong)

    def test_offline_transition_and_recovery(self):
        g = self.guard
        for _ in range(2):
            g.update(False, "pong_timeout")
            self.assertEqual(g.state, "degraded")
        g.update(False, "pong_timeout")
        self.assertEqual(g.state, "offline")
        self.assertEqual(self.admin_notices, [False])
        g.update(False, "pong_timeout")
        self.assertEqual(self.admin_notices, [False])
        g.update(True, "pong_received")
        self.assertEqual(g.state, "online")
        self.assertEqual(g.failures, 0)
        self.assertEqual(self.admin_notices, [False, True])
        state = json.loads(g.status_file.read_text())
        self.assertEqual(state["profile"], "unittest")
        self.assertEqual(state["state"], "online")
        self.assertEqual(g.status_file.stat().st_mode & 0o777, 0o600)

    def test_immediate_pong_before_send_returns(self):
        g = self.guard
        captured = []
        def send(text):
            captured.append(text)
            g.process_message(self.message("PONG"))
        mp = types.SimpleNamespace(send=send)
        account = types.SimpleNamespace(search=lambda name: [mp])
        bot = types.SimpleNamespace(mps=lambda: account)
        self.coordinator.slaves = {"blueset.wechat": types.SimpleNamespace(bot=bot)}
        g.probe()
        self.assertEqual(captured, ["PING"])
        self.assertEqual(g.state, "online")
        self.assertEqual(g.failures, 0)

    def test_missing_wechat_instance_is_a_failure_not_crash(self):
        self.guard.probe()
        self.assertEqual(self.guard.state, "degraded")
        self.assertEqual(self.guard.reason, "wechat_bot_not_ready")


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    unittest.main()
