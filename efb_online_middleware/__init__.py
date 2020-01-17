# coding: utf-8
import io
import os
import re
import time
import sched
import string
import logging
import threading

from typing import Optional
from ruamel.yaml import YAML

from ehforwarderbot import Middleware, Message, \
    coordinator, Channel, utils

from efb_wechat_slave.vendor import wxpy

from .__version__ import __version__ as version

DALAY_HEART_BEAT = 1800     # half an hour
PING_STATUS = 'PING'
PONG_STATUS = 'PONG'

global CHANNEL_ETM_BOT, CHANNEL_EWS, ADMIN_ID

ping_status = ''
failure_time = 0
dalay_heart_beat = DALAY_HEART_BEAT
warn_status = False

echo_mp = ''
ping_text = 'PING'
pong_text = 'PONG'

find_mp_fail_tip = False

class OnlineMiddleware(Middleware):
    """
    EFB Middleware - OnlineMiddleware
    """

    middleware_id = "online.OnlineMiddleware"
    middleware_name = "Online Middleware"
    __version__: str = version

    logger: logging.Logger = logging.getLogger("plugins.%s" % middleware_id)

    def __init__(self, instance_id=None):
        global CHANNEL_ETM_BOT, ADMIN_ID, CHANNEL_EWS
        super().__init__()
        self.load_config()

        if hasattr(coordinator, "master") and isinstance(coordinator.master, Channel):
            self.channel = coordinator.master
            CHANNEL_ETM_BOT = self.channel.bot_manager
            ADMIN_ID = self.channel.config['admins'][0]
            # CHANNEL_ETM_BOT.send_message(ADMIN_ID, 'msg')

        if hasattr(coordinator, "slaves") and coordinator.slaves['blueset.wechat']:
            CHANNEL_EWS = coordinator.slaves['blueset.wechat']

            try:
                schedule_heart_beat()

            except Exception as e:
                self.logger.log(99, 'failed to schedule: {}'.format(e))

    def load_config(self):
        """
        Load configuration from path specified by the framework.

        Configuration file is in YAML format.
        """
        global echo_mp, ping_text, pong_text, dalay_heart_beat, DALAY_HEART_BEAT

        config_path = utils.get_config_path(self.middleware_id)
        if not config_path.exists():
            return

        with config_path.open() as f:
            data = YAML().load(f)

            # Verify configuration
            echo_mp = data.get("echo_mp")
            if not echo_mp:
                raise ValueError("echo mp is needed.")

            DALAY_HEART_BEAT = int(data.get("interval", DALAY_HEART_BEAT))
            ping_text = data.get("ping", ping_text)
            pong_text = data.get("pong", pong_text)

            dalay_heart_beat = DALAY_HEART_BEAT

    def sent_by_master(self, message: Message) -> bool:
        author = message.author
        return author and author.module_id and author.module_id == 'blueset.telegram'

    def process_message(self, message: Message) -> Optional[Message]:
        """
        Process a message with middleware
        Args:
            message (:obj:`.Message`): Message object to process
        Returns:
            Optional[:obj:`.Message`]: Processed message or None if discarded.
        """
        global ping_status, failure_time, dalay_heart_beat, warn_status, find_mp_fail_tip

        if self.sent_by_master(message):
            return message

        author = message.author
        if author:
            # self.logger.log( 99, "message.author: %s", message.author.__dict__)
            if author.name == echo_mp and message.text == pong_text and ping_status == PING_STATUS:
                ping_status = PONG_STATUS
                failure_time = 0
                dalay_heart_beat = DALAY_HEART_BEAT
                warn_status = False
                find_mp_fail_tip = False
                return None
            if message.text == pong_text:
                self.logger.log( 99, "Echo msg: %s, ping_status: %s", message.__dict__, ping_status)

        return message


def schedule_heart_beat():

    schedule = sched.scheduler(time.time, time.sleep)
    schedule.enter(dalay_heart_beat, 0, heart_beat, ())

    threading.Thread(target=schedule.run).start()


def heart_beat():
    global ping_status, failure_time, dalay_heart_beat, warn_status

    if ping_status == PING_STATUS:
        failure_time += 1

        if not warn_status:
            dalay_heart_beat = 10

    if failure_time > 2 and not warn_status:
        send_tip_message()
        warn_status = True
        dalay_heart_beat = DALAY_HEART_BEAT

    schedule_heart_beat()

    try:
        echo_chat = get_echo_chat()
        ping_status = PING_STATUS
        echo_chat.send(ping_text)

    except ValueError:
        if not find_mp_fail_tip:
            CHANNEL_ETM_BOT.send_message(ADMIN_ID, '微信可能已掉线，请检查')

    except Exception:
        logger.exception('echo failed.')


def get_echo_chat():
    return wxpy.utils.ensure_one(CHANNEL_EWS.bot.mps().search(echo_mp))


def send_tip_message():
    CHANNEL_ETM_BOT.send_message(ADMIN_ID, '微信可能已掉线，请检查')
