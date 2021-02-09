#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
:file           utils.py
:project        bilibili_live_utils
:name           Utilities
:author         Doby2333
:github         https://github.com/lyzhang0113/bilibili-live-utils
:version        1.0.0
:created        2021/02/06 14:18
:description    通用的工具方法放在这里
"""
import asyncio
import os
import logging
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from configparser import RawConfigParser
from bilibili_api import live

# Constants
guard_name = {0: "用户", 1: "总督", 2: "提督", 3: "舰长"}  # 大航海类型映射关系


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


def config_check(config: RawConfigParser, path: str):
    """
    检查是否存在运行需要的配置文件和相关配置，如果不存在，退出运行。

    :param config: RawConfigParser 配置文件类
    :param path: 要读取的配置文件路径
    :return: None
    :raise AssertionError 配置文件有误时抛出异常
    """
    assert os.path.exists(path), \
        '没有找到配置文件 ' + path + ' ！'
    assert len(config.read(path, encoding='utf-8')) > 0, \
        '读取配置文件 ' + path + ' 失败！请确认 ' + path + ' 存在且编码格式为 utf-8 ！'
    assert config.has_option('LIVE', 'ROOM_ID'), \
        '配置文件缺少 [LIVE] 中的 ROOM_ID 属性，请指定要链接的直播间号码！'
    assert config.has_option('USER', 'SESSDATA'), \
        '配置文件缺少 [USER] 中的 SESSDATA 属性，请指定登陆用户的 SESSDATA ！'
    assert config.has_option('USER', 'BILIBILI_JCT'), \
        '配置文件缺少 [USER] 中的 CSRF 属性，请指定登陆用户的 CSRF ！'
    assert config.has_option('LOG', 'LEVEL'), \
        '配置文件缺少 [LOG] 中的 LEVEL 属性，请指定程序日志等级！'
    assert config.has_option('LOG', 'FORMAT'), \
        '配置文件缺少 [LOG] 中的 FORMAT 属性，请指定程序日志格式！'
    assert config.has_option('DANMAKU', 'WELCOME_ENTER'), \
        '配置文件缺少 [DANMAKU] 中的 WELCOME_ENTER 属性！'
    assert config.has_option('DANMAKU', 'WELCOME_GUARD'), \
        '配置文件缺少 [DANMAKU] 中的 WELCOME_GUARD 属性！'
    assert config.has_option('DANMAKU', 'THANK_GIFT'), \
        '配置文件缺少 [DANMAKU] 中的 THANK_GIFT 属性！'
    assert config.has_option('DANMAKU', 'THANK_GUARD'), \
        '配置文件缺少 [DANMAKU] 中的 THANK_GUARD 属性！'
    assert config.has_option('DANMAKU', 'THANK_SC'), \
        '配置文件缺少 [DANMAKU] 中的 THANK_SC 属性！'
    assert config.has_option('DANMAKU', 'SCHEDULED_INTERVAL'), \
        '配置文件缺少 [DANMAKU] 中的 SCHEDULED_INTERVAL 属性！请指定定时弹幕的发送间隔！'
    assert config.has_option('TURING_AI', 'ENABLE'), \
        '配置文件缺少 [TURING_AI] 中的 ENABLE 属性！请指定是否启用图灵机器人！'
    if not config.getboolean('TURING_AI', 'ENABLE'):
        return
    assert config.has_option('TURING_AI', 'QUESTION_PREFIX'), \
        '配置文件缺少 [TURING_AI] 中的 QUESTION_PREFIX 属性！请指定图灵机器人监听的弹幕前缀！'
    assert config.has_option('TURING_AI', 'ANSWER_PREFIX'), \
        '配置文件缺少 [TURING_AI] 中的 ANSWER_PREFIX 属性！请指定图灵机器人回复时的弹幕前缀！'
    assert config.has_option('TURING_AI', 'API_URL'), \
        '配置文件缺少 [TURING_AI] 中的 API_URL 属性！请指定图灵机器人的API地址！'
    assert config.has_option('TURING_AI', 'API_KEYS'), \
        '配置文件缺少 [TURING_AI] 中的 API_KEYS 属性！请指定图灵机器人的 API_KEY ！'
    assert config.has_option('TURING_AI', 'REQUEST_FORMAT'), \
        '配置文件缺少 [TURING_AI] 中的 REQUEST_FORMAT 属性！请指定图灵机器人的请求模板！'


def get_dahanghai_dict(room_id: int):
    """
    获取指定直播间的大航海成员字典
    :param room_id: 直播间ID
    :return: 包含所有大航海成员的字典 {uid: 大航海等级}
    """
    return {r['uid']: r['guard_level'] for r in live.get_dahanghai(room_id)}


class TrimColorFormatter(logging.Formatter):
    """
    去除ANSI颜色标记
    """
    def format(self, record: logging.LogRecord) -> str:
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        record.msg = ansi_escape.sub('', record.msg)
        return super(TrimColorFormatter, self).format(record)
