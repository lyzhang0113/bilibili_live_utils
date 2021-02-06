#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
:file           danmaku_sender.py
:project        bilibili_live_utils
:name           弹幕发送服务
:author         Doby2333
:github         https://github.com/lyzhang0113/bilibili-live-utils
:version        1.0
:created        2021/01/31
:description    使用账号信息和房间号进行初始化后，可以向该房间发送指定格式弹幕
"""

import asyncio
import sys
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from termcolor import colored
from bilibili_api import *


class DanmakuSender(object):

    def __init__(self, room_id: int, verify: Verify, min_interval: int = 3000):
        """
        初始化弹幕姬，传入用户验证信息和房间号
        :type verify: Verify 登陆用户的Verify类
        :type room_id: int 需要连接的房间号
        :type min_interval: int 需要发送的两条弹幕之间的最小间隔时间ms
        """
        self.room_id = room_id
        self.verify = verify
        self.__prev_time = datetime.now()
        self.minimal_send_interval = min_interval
        self._log = logging.getLogger('')

    def welcome_enter(self, uname):
        """
        欢迎用户进入直播间
        :type uname: str 进入直播间的用户的用户名
        """
        content = "欢迎" + uname + "进入直播间"
        self.send(Danmaku(text=content, mode=Danmaku.MODE_BOTTOM, font_size=Danmaku.FONT_SIZE_SMALL))

    def welcome_guard(self, uname, guard_type):
        """
        欢迎大航海进入直播间
        :type uname: str 进入直播间的用户的用户名
        :type guard_type: str 大航海级别（字符串）
        """
        content = "喵~欢迎" + guard_type + uname + "进入直播间签到"
        self.send(Danmaku(text=content, mode=Danmaku.MODE_BOTTOM, font_size=Danmaku.FONT_SIZE_SMALL), True)

    def thanks_gift(self, uname, giftname, num):
        """
        感谢用户的礼物
        :type uname: str 赠送礼物的用户的用户名
        :type giftname: str 赠送的礼物名称
        :type num: int 赠送的礼物数量
        """
        content = "感谢" + uname + "投喂的" + giftname + "x" + str(num)
        self.send(Danmaku(text=content, mode=Danmaku.MODE_TOP, font_size=Danmaku.FONT_SIZE_SMALL))

    def thanks_guard(self, uname, giftname, num):
        """
        感谢上舰
        :type uname: str 开通大航海的用户的用户名
        :type giftname: str 开通的大航海类型（字符串）
        :type num: int 开通的月数
        """
        content = "感谢" + uname + "开通的" + str(num) + "个月" + giftname + "！老板断气！"
        self.send(Danmaku(text=content, mode=Danmaku.MODE_TOP, font_size=Danmaku.FONT_SIZE_NORMAL), True)

    def thanks_sc(self, uname):
        """
        感谢醒目留言
        :type uname: str 发送形目留言的用户的用户名
        """
        content = "感谢" + uname + "发送的醒目留言！老板断气"
        self.send(Danmaku(text=content, mode=Danmaku.MODE_TOP, font_size=Danmaku.FONT_SIZE_NORMAL), True)

    # def subscribe_notice(self):
    #     """
    #     提醒关注~
    #     """
    #     content = "欢迎新来的小伙伴~如果喜欢主播这样的可爱神兽可以点波关注哦~"
    #     self.send(Danmaku(text=content, mode=Danmaku.MODE_TOP, font_size=Danmaku.FONT_SIZE_SUPER_SMALL), False)

    def send_text(self, text):
        """
        对于可能出现的过长弹幕（如用户输入、AI回复）
        使用此方法可以自动以30个字拆分弹幕并发送
        :param text: 要发送的弹幕内容（可以超过30个字）
        """
        chunks = [text[i:i + 30] for i in range(0, len(text), 30)]
        self._log.debug(str(chunks))
        for chunk in chunks:
            if chunk != "":
                self.send(danmaku=Danmaku(text=chunk, mode=Danmaku.MODE_FLY, font_size=Danmaku.FONT_SIZE_NORMAL),
                          important=True)
                time.sleep(1.5)

    def send(self, danmaku: Danmaku, important=False):
        """
        发送弹幕，有最短间隔时间
        :param console_input: 是否是控制台输入的弹幕
        :type danmaku: Danmaku
        :type important: bool
        """
        try:
            self._log.info(colored(str("【发送弹幕】" + danmaku.text), 'red', 'on_green'))
            time_delta = datetime.now() - self.__prev_time
            if time_delta.microseconds < self.minimal_send_interval and not important:
                self._log.warning(colored(str("【弹幕发送失败，间隔太短】" + str(time_delta.microseconds) + "ms"), 'yellow', 'on_red'))
                return
            live.send_danmaku(room_real_id=self.room_id, danmaku=danmaku, verify=self.verify)
            self.__prev_time = datetime.now()
        except Exception as e:
            self._log.error("弹幕发送失败！" + str(e))


async def ainput(prompt: str = ""):
    """
    异步等待用户输入
    :param prompt: 提示语
    :return: 用户输入的内容
    """
    with ThreadPoolExecutor(1, "AsyncInput", lambda x: print(x, end="", flush=True), (prompt,)) as executor:
        return (await asyncio.get_event_loop().run_in_executor(
            executor, sys.stdin.readline
        )).rstrip()


async def start_console_sender(ds: DanmakuSender):
    """
    启用控制台发送弹幕。无限循环等待用户输入，输入后发送弹幕。
    :param ds: DanmakuSender 弹幕发送类
    """
    while True:
        ds.send_text(await ainput())
