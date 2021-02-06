#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
:file           main.py
:name           直播弹幕姬工具主程序入口
:author         Doby2333
:version        1.0
:created        2021/01/31
:edited         2021/02/06 14:14
:description
"""

import os
import sys
import logging
import asyncio
import random
from configparser import RawConfigParser
from datetime import date

from termcolor import colored
from apscheduler.schedulers.background import BackgroundScheduler
from bilibili_api import Verify
from bilibili_api import live

import utils
from turing_ai import TuringAI
import danmaku_sender

# 配置文件存放路径，默认为同目录的 config.ini 文件
config_path = 'config.ini'

# 全局变量提前声明一下提高可读性
config: RawConfigParser  # 配置文件
log: logging.Logger  # 日志
verify: Verify  # Bilibili 登录信息
room: live.LiveDanmaku  # 监听事件的直播间对象
ds: danmaku_sender.DanmakuSender  # 弹幕发送器
turing: TuringAI  # 图灵机器人
scheduler: BackgroundScheduler  # 定时任务

room_id: int  # 连接的直播间房间号
uname: str  # 主播名字
fan_medal: str  # 连接直播间的粉丝牌名
isStreaming: bool  # 当前是否在直播
dahanghai_dict: dict  # 存放当前大航海成员的字典（每日凌晨重置）{uid: 大航海级别}
welcomed_list: list  # 已经欢迎过的观众列表（下播时重置）

"""
初始化：配置文件读取、日志记录器设置
"""
try:
    # 检查并读取配置文件
    config = RawConfigParser()
    utils.config_check(config, config_path)

    # 初始化日志记录器
    log = logging.getLogger('')
    log.setLevel(config.get('LOG', 'LEVEL'))

    # 写入日志到文件
    log_file = config.get('LOG', 'FILE')  # 获取输出日志文件路径，并生成日志文件名
    if log_file != '':
        log_file = log_file.replace('${room_id}', config.get('LIVE', 'ROOM_ID')).replace('${date}', str(date.today()))
        log_file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        log_file_handler.setFormatter(utils.TrimColorFormatter(config.get('LOG', 'FORMAT')))
        log.addHandler(log_file_handler)
    # 输出日志到控制台
    log_console_handler = logging.StreamHandler(sys.stdout)
    log_console_handler.setFormatter(logging.Formatter(config.get('LOG', 'FORMAT')))
    log.addHandler(log_console_handler)
    log.info("配置文件 " + config_path + " 读取成功！" + "当前日志记录等级：" + logging.getLevelName(log.level))
except Exception as exception:
    print(colored(text="程序初始化错误：" + str(exception), color='red', attrs=('bold',)))
    os.system("PAUSE")
    sys.exit(1)

"""
读取配置文件，初始化全局变量，做连接到直播间前的准备
"""
# 初始化全局变量
room_id = config.getint('LIVE', 'ROOM_ID')
verify = Verify(sessdata=config.get('USER', 'SESSDATA'), csrf=config.get('USER', 'BILIBILI_JCT'))
room = live.LiveDanmaku(room_display_id=room_id, verify=verify)
ds = danmaku_sender.DanmakuSender(room_id=room_id, verify=verify)
scheduler = BackgroundScheduler()
turing = TuringAI(api_url=config.get('TURING_AI', 'API_URL'),
                  api_keys=config.get('TURING_AI', 'API_KEYS').split(','),
                  request_body=config.get('TURING_AI', 'REQUEST_FORMAT'))
# 查询API获取初始化需要的数据
room_info = live.get_room_info(room_id, verify)
isStreaming = room_info['room_info']['live_status'] == 1
uname = room_info['anchor_info']['base_info']['uname']
fan_medal = room_info['anchor_info']['medal_info']['medal_name']
log.info("连接到[" + uname + "]的直播间[" + str(room_id) + "]，当前直播状态：" + ("直播中" if isStreaming else "未开播"))
dahanghai_dict = utils.get_dahanghai_dict(room_id)
log.info("查询到当前大航海存在" + str(len(dahanghai_dict)) + "个成员")


@room.on("DANMU_MSG")  # 收到弹幕
async def on_danmu(msg):
    log.debug(msg)
    uid = str(msg['data']['info'][2][0])
    uname = msg['data']['info'][2][1]
    content = str(msg['data']['info'][1])
    log.info(colored(str("【收到弹幕】" + uname + ": " + content), 'blue'))
    # TODO: AI机器人？
    pass


@room.on("INTERACT_WORD")  # 用户进入
async def on_enter(msg):
    log.debug(msg)
    uid = msg['data']['data']['uid']    # UID
    uname = msg['data']['data']['uname']    # 用户名
    fans_rank = msg['data']['data']['fans_medal']['medal_level']    # 粉丝牌等级
    fans_name = msg['data']['data']['fans_medal']['medal_name']     # 粉丝牌名字
    is_guard = True if (uid in dahanghai_dict) else False   # 是否是大航海成员
    guard_level = dahanghai_dict[uid] if is_guard else ''    # 大航海级别
    if uid not in welcomed_list:
        # TODO: 判断更多欢迎条件
        # TODO: 执行欢迎
        log.info("欢迎" + uname + guard_level + "进入直播间")
        pass

    # 添加至list以避免重复欢迎
    if config.getboolean('DANMAKU', 'ONLY_WELCOME_ONCE'):
        welcomed_list.append(uid)
    pass


@room.on("SUPER_CHAT_MESSAGE")  # 醒目留言
async def on_sc(msg):
    log.debug(msg)
    uid = msg['data']['data']['uid']
    uname = msg['data']['data']['user_info']['uname']
    content = msg['data']['data']['message']
    price = msg['data']['data']['price']
    pass


@room.on("SEND_GIFT")  # 收到礼物
async def on_gift(msg):
    log.debug(msg)
    uid = msg['data']['data']['uid']
    num = msg['data']['data']['num']
    uname = msg['data']['data']['uname']
    giftname = msg['data']['data']['giftName']
    total_coin = msg['data']['data']['total_coin']
    coin_type = msg['data']['data']['coin_type']
    fans_rank = msg['data']['data']['medal_info']['medal_level']
    fans_name = msg['data']['data']['medal_info']['medal_name']
    log.info("感谢" + uname + "赠送的" + giftname + "x" + str(num))
    pass


@room.on("COMBO_SEND")  # 礼物连击
async def on_gift_combo(msg):
    log.debug(msg)
    uid = msg['data']['data']['uid']
    uname = msg['data']['data']['uname']
    # r_uname = msg['data']['data']['r_uname']
    giftname = msg['data']['data']['gift_name']
    total_num = msg['data']['data']['total_num']
    coin = msg['data']['data']['combo_total_coin']
    pass


@room.on("GUARD_BUY")  # 收到大航海
async def on_gift(msg):
    global dahanghai_dict
    log.debug(msg)
    uid = msg['data']['data']['uid']
    uname = msg['data']['data']['username']
    guard_level = msg['data']['data']['guard_level']
    num = msg['data']['data']['num']
    price = msg['data']['data']['price']
    gift_name = msg['data']['data']['gift_name']

    dahanghai_dict = utils.get_dahanghai_dict(room_id=room_id) # 刷新大航海表
    log.info(colored(str("【感谢" + gift_name + "】" + uname + ' ' + str(num) + '个月 ￥' + str(price / 1000)), 'red'))
    pass


@room.on("PREPARING")  # 直播结束
async def on_prepare(msg):
    global isStreaming
    log.debug(msg)
    log.warning(colored("********************【直播结束】********************", 'red', 'on_yellow'))
    isStreaming = False
    welcomed_list.clear()
    pass


@room.on("LIVE")  # 直播开始
async def on_live(msg):
    global isStreaming
    log.debug(msg)
    log.warning(colored("********************【直播开始】********************", 'red', 'on_yellow'))
    isStreaming = True
    welcomed_list.clear()
    pass


@room.on("ROOM_REAL_TIME_MESSAGE_UPDATE")  # 粉丝数更新
async def on_fans_update(msg):
    log.debug(msg)
    log.info("粉丝数更新")
    pass


# 每日零点刷新大航海列表
@scheduler.scheduled_job(trigger='cron', id='new_day_job', misfire_grace_time=10, hour='0', minute='0', second='5')
def new_day_job():
    global dahanghai_dict
    log.info("到点了，刷新大航海列表")
    dahanghai_dict = utils.get_dahanghai_dict(room_id=room_id)


# 发送定时弹幕
@scheduler.scheduled_job(trigger='interval', id='interval_job', minutes=config.getint('DANMAKU', 'SCHEDULED_INTERVAL'))
def interval_job():
    if isStreaming:
        log.info("定时弹幕已触发")
        # ds.send_text(random.choice(config.get('DANMAKU', 'SCHEDULED_NOTICE').split(',')))


if __name__ == '__main__':
    # 启动控制台可以发送弹幕的功能
    log.info("在控制台直接输入内容即可发送弹幕！")
    asyncio.get_event_loop().create_task(danmaku_sender.start_console_sender(ds))
    # 启动定时任务
    scheduler.start()
    # 连接至直播间，并监听事件
    try:
        room.connect()
    except Exception as e:
        log.critical("致命错误：直播间重连失败！即将退出程序，需要手动重启！" + str(e))
    finally:
        os.system("PAUSE")
        sys.exit(0)
