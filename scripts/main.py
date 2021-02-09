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
from bilibili_api import live, user

from scripts import utils, danmaku_sender
from scripts.turing_ai import TuringAI

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
up_name: str  # 主播名字
fan_medal: str  # 连接直播间的粉丝牌名
isStreaming: bool  # 当前是否在直播
dahanghai_dict = {}  # 存放当前大航海成员的字典（每日凌晨重置）{uid: 大航海级别}
welcomed_list = []  # 已经欢迎过的观众列表（下播时重置）

"""
**************************************************************************
****************** 初始化：配置文件验证有效、日志记录器设置 *******************
**************************************************************************
"""
os.system('chcp 65001')  # 使控制台用utf-8编码
try:
    # 检查并读取配置文件
    config = RawConfigParser()
    utils.config_check(config, config_path)

    # 初始化日志记录器
    log = logging.getLogger('bilibili_live_utils')
    log.setLevel(config.get('LOG', 'LEVEL'))

    # 输出日志到控制台
    log_console_handler = logging.StreamHandler(sys.stdout)
    log_console_handler.setFormatter(logging.Formatter(config.get('LOG', 'FORMAT')))
    log.addHandler(log_console_handler)
    log.info("配置文件 " + config_path + " 读取成功！" + "日志记录等级：" + colored(logging.getLevelName(log.level), attrs=['bold', ]))
    # 写入日志到文件
    log_file = config.get('LOG', 'FILE')  # 获取输出日志文件路径，并生成日志文件名
    if log_file != '':
        log_file = log_file.replace('${room_id}', config.get('LIVE', 'ROOM_ID')).replace('${date}', str(date.today()))
        if os.path.dirname(log_file) != '':
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
        log.info("输出日志到：" + colored(os.path.abspath(log_file), attrs=['bold', ]))
        log_file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        log_file_handler.setFormatter(utils.TrimColorFormatter(config.get('LOG', 'FORMAT')))
        log.addHandler(log_file_handler)
except Exception as exception:
    print(colored(text="程序初始化错误：" + str(exception), color='red', on_color='on_green', attrs=('bold', )))
    os.system("PAUSE")
    sys.exit(1)

"""
**************************************************************************
********** 初始化：读取配置文件，初始化全局变量，做连接到直播间前的准备 *********
**************************************************************************
"""
# 初始化全局变量
room_id = config.getint('LIVE', 'ROOM_ID')
verify = Verify(sessdata=config.get('USER', 'SESSDATA'), csrf=config.get('USER', 'BILIBILI_JCT'))
room = live.LiveDanmaku(room_display_id=room_id, verify=verify)
ds = danmaku_sender.DanmakuSender(room_id=room_id, verify=verify, enable=config.getboolean('DANMAKU', 'ENABLE'))
scheduler = BackgroundScheduler()
turing = TuringAI(api_url=config.get('TURING_AI', 'API_URL'),
                  api_keys=config.get('TURING_AI', 'API_KEYS').split(','),
                  request_body=config.get('TURING_AI', 'REQUEST_FORMAT'),
                  enable=config.getboolean('TURING_AI', 'ENABLE'))
# 查询API获取初始化需要的数据
# TODO: 已登录用户xxx
room_info = live.get_room_info(room_id, verify)
isStreaming = room_info['room_info']['live_status'] == 1
up_name = room_info['anchor_info']['base_info']['uname']
fan_medal = room_info['anchor_info']['medal_info']['medal_name']
log.info("连接到 [" + up_name + "] 的直播间 [" + str(room_id) + "] ，当前直播状态：" + colored("直播中" if isStreaming else "未开播", attrs=['bold', ]))
dahanghai_dict = utils.get_dahanghai_dict(room_id)
log.info("初始化大航海成员字典成功！当前船上有" + str(len(dahanghai_dict)) + "个成员")
# TODO: 输出当前关键配置，供用户知晓；如登陆的用户信息等
log.info(colored("************************** 初始化完毕 **************************", color='red', attrs=['bold', ]))

"""
**************************************************************************
**************************** 定义直播间事件触发 ****************************
**************************************************************************
"""


# {'room_display_id': 732, 'room_real_id': 6154037, 'type': 'VIEW', 'data': 113791}
@room.on("VIEW") # 直播间人气更新
async def on_view(msg):
    viewer_num = msg['data']
    log.info("【人气更新】当前直播间人气 " + colored(str(viewer_num), attrs=['bold', ]))


# {'room_display_id': 732, 'room_real_id': 6154037, 'type': 'NOTICE_MSG', 'data': {'cmd': 'NOTICE_MSG', 'full': {'head_icon': 'http://i0.hdslb.com/bfs/live/b29add66421580c3e680d784a827202e512a40a0.webp', 'tail_icon': 'http://i0.hdslb.com/bfs/live/822da481fdaba986d738db5d8fd469ffa95a8fa1.webp', 'head_icon_fa': 'http://i0.hdslb.com/bfs/live/49869a52d6225a3e70bbf1f4da63f199a95384b2.png', 'tail_icon_fa': 'http://i0.hdslb.com/bfs/live/38cb2a9f1209b16c0f15162b0b553e3b28d9f16f.png', 'head_icon_fan': 24, 'tail_icon_fan': 4, 'background': '#66A74EFF', 'color': '#FFFFFFFF', 'highlight': '#FDFF2FFF', 'time': 20}, 'half': {'head_icon': 'http://i0.hdslb.com/bfs/live/ec9b374caec5bd84898f3780a10189be96b86d4e.png', 'tail_icon': '', 'background': '#85B971FF', 'color': '#FFFFFFFF', 'highlight': '#FDFF2FFF', 'time': 15}, 'side': {'head_icon': '', 'background': '', 'color': '', 'highlight': '', 'border': ''}, 'roomid': 156536, 'real_roomid': 156536, 'msg_common': '<円円__>投喂<一心X_IN>1个小电视飞船，点击前往TA的房间吧！', 'msg_self': '<円円__>投喂<一心X_IN>1个小电视飞船，快来围观吧！', 'link_url': 'https://live.bilibili.com/156536?from=28003&extra_jump_from=28003&live_lottery_type=1&broadcast_type=1', 'msg_type': 2, 'shield_uid': -1, 'business_id': '25', 'scatter': {'min': 0, 'max': 0}}}
@room.on("NOTICE_MSG") # 全频道通知
async def on_notice(msg):
    pass


# {'room_display_id': 732, 'room_real_id': 6154037, 'type': 'DANMU_MSG', 'data': {'cmd': 'DANMU_MSG', 'info': [[0, 1, 25, 12802438, 1612863232120, 1612862943, 0, 'b80e5623', 0, 0, 2, '#19897EFF,#403F388E,#33897EFF'], '感觉可以的', [7930172, 'AのFa', 0, 1, 1, 10000, 1, '#E17AFF'], [30, 'ASAKI', 'Asaki大人', 6154037, 2951253, '', 1000006, 16771156, 2951253, 10329087, 2, 1, 194484313], [50, 0, 16746162, 6331, 1], ['title-279-1', 'title-279-1'], 0, 2, None, {'ts': 1612863232, 'ct': '684B0420'}, 0, 0, None, None, 0]}}
@room.on("DANMU_MSG")  # 收到弹幕
async def on_danmaku(msg):
    uid = str(msg['data']['info'][2][0])
    uname = msg['data']['info'][2][1]
    content = str(msg['data']['info'][1])
    log.info(colored(str("【收到弹幕】" + uname + ": " + content), 'blue'))
    # AI机器人
    q_prefix = config.get('TURING_AI', 'QUESTION_PREFIX')
    if content.startswith(q_prefix):
        try:
            ds.send_text(config.get('TURING_AI', 'ANSWER_PREFIX') + turing.ask(content.replace(q_prefix, ''), uid))
        except Exception as turing_exception:
            log.warning(colored(turing_exception, 'yellow', 'on_magenta', ['bold', ]))
            ds.send_text(config.get('TURING_AI', 'ANSWER_PREFIX') + config.get('TURING', 'FALLBACK'))


# {'room_display_id': 732, 'room_real_id': 6154037, 'type': 'INTERACT_WORD', 'data': {'cmd': 'INTERACT_WORD', 'data': {'uid': 298047096, 'uname': '德物昂Duang', 'uname_color': '', 'identities': [3, 1], 'msg_type': 1, 'roomid': 6154037, 'timestamp': 1612862503, 'score': 1612872706213, 'fans_medal': {'target_id': 168598, 'medal_level': 2, 'medal_name': '刺儿', 'medal_color': 6067854, 'medal_color_start': 6067854, 'medal_color_end': 6067854, 'medal_color_border': 6067854, 'is_lighted': 1, 'guard_level': 0, 'special': '', 'icon_id': 0, 'anchor_roomid': 1017, 'score': 203}, 'is_spread': 0, 'spread_info': '', 'contribution': {'grade': 0}, 'spread_desc': '', 'tail_icon': 0}}}
@room.on("INTERACT_WORD")  # 用户进入（更新后大航海成员进入时不会触发该事件！）
async def on_user_enter(msg):
    uid = msg['data']['data']['uid']  # UID
    uname = msg['data']['data']['uname']  # 用户名
    medal_level = msg['data']['data']['fans_medal']['medal_level']  # 粉丝牌等级
    medal_name = msg['data']['data']['fans_medal']['medal_name']  # 粉丝牌名字
    is_lighted = msg['data']['data']['fans_medal']['is_lighted'] == 1 # 粉丝牌是否为点亮状态
    guard_level = msg['data']['data']['fans_medal']['guard_level'] # 粉丝牌的大航海等级（3：舰长，... ）
    anchor_roomid = msg['data']['data']['fans_medal']['anchor_roomid'] # 粉丝牌所属房间号

    # 获取进入用户的关注信息
    user_relation = user.get_relation_info(uid=uid, verify=verify)
    following = user_relation['following'] # 关注数
    follower = user_relation['follower'] # 粉丝数
    if uid not in welcomed_list:
        log.info(colored("【用户进入】" + uname, 'white'))
        # 粉丝数大于10000 或 持有当前房间粉丝牌大于5级
        if follower >= 10000 or (anchor_roomid == room_id and medal_level >= 5):
            user_info = user.get_user_info(uid=uid, verify=verify)
            sex = user_info['sex']  # '男', '女', '保密'
            level = user_info['level']  # B站等级
            ds.welcome_enter(uname, sex)

            # 添加至list以避免重复欢迎
            if config.getboolean('DANMAKU', 'ONLY_WELCOME_ONCE'):
                welcomed_list.append(uid)


# {'room_display_id': 22603751, 'room_real_id': 22603751, 'type': 'ENTRY_EFFECT', 'data': {'cmd': 'ENTRY_EFFECT', 'data': {'id': 4, 'uid': 39832030, 'target_id': 351799197, 'mock_effect': 0, 'face': 'https://i1.hdslb.com/bfs/face/a2dd3d0cd432b74ef21f5c37c78b4d9865f3455c.jpg', 'privilege_type': 3, 'copy_writing': '欢迎舰长 <%小馋狮%> 进入直播间', 'copy_color': '#ffffff', 'highlight_color': '#E6FF00', 'priority': 1, 'basemap_url': 'https://i0.hdslb.com/bfs/live/mlive/f34c7441cdbad86f76edebf74e60b59d2958f6ad.png', 'show_avatar': 1, 'effective_time': 2, 'web_basemap_url': '', 'web_effective_time': 0, 'web_effect_close': 0, 'web_close_time': 0, 'business': 1, 'copy_writing_v2': '欢迎舰长 <%小馋狮%> 进入直播间', 'icon_list': [], 'max_delay_time': 7}}}
@room.on("ENTRY_EFFECT")  # 一路火花带闪电地进入直播间（一般是大航海成员）
async def on_guard_enter(msg):
    uid = msg['data']['data']['uid'] # 用户UID
    up_uid = msg['data']['data']['target_id'] # 主播的UID
    guard_type = utils.guard_name[msg['data']['data']['privilege_type']] # 用户在该直播间的大航海等级（3：舰长，... ）
    copy_writing = str(msg['data']['data']['copy_writing']) # "欢迎舰长 <%uname%> 进入直播间"
    start = copy_writing.find('<%') + 2
    uname = copy_writing[start:copy_writing.find('%>', start)] # 进入直播间的用户名
    log.info(colored("【" + guard_type + "进入】" + uname, 'green'))
    ds.welcome_guard(uname, guard_type)


@room.on("SUPER_CHAT_MESSAGE")  # 醒目留言
async def on_super_chat(msg):
    uid = msg['data']['data']['uid']
    uname = msg['data']['data']['user_info']['uname']
    content = msg['data']['data']['message']
    price = msg['data']['data']['price']
    log.info(colored(str("【醒目留言】￥" + str(price) + '\t' + uname + ": " + content), 'red'))
    ds.thanks_sc(uname)


# {'room_display_id': 732, 'room_real_id': 6154037, 'type': 'SEND_GIFT', 'data': {'cmd': 'SEND_GIFT', 'data': {'draw': 0, 'gold': 0, 'silver': 0, 'num': 1, 'total_coin': 0, 'effect': 0, 'broadcast_id': 0, 'crit_prob': 0, 'guard_level': 0, 'rcost': 272777534, 'uid': 383665082, 'timestamp': 1612862911, 'giftId': 30607, 'giftType': 5, 'super': 0, 'super_gift_num': 23, 'super_batch_gift_num': 23, 'remain': 1, 'price': 0, 'beatId': '', 'biz_source': 'Live', 'action': '投喂', 'coin_type': 'silver', 'uname': 'Akatuと', 'face': 'http://i0.hdslb.com/bfs/face/175b45e7c3535b39f2d8af44924dab3a2286a904.jpg', 'batch_combo_id': 'batch:gift:combo_id:383665082:194484313:30607:1612862906.4710', 'rnd': 'FFE5B5D2-9626-4A4F-950D-75BF3B75555E', 'giftName': '小心心', 'combo_send': None, 'batch_combo_send': None, 'tag_image': '', 'top_list': None, 'send_master': None, 'is_first': False, 'demarcation': 1, 'combo_stay_time': 3, 'combo_total_coin': 1, 'tid': '1612862911130200004', 'effect_block': 1, 'is_special_batch': 0, 'combo_resources_id': 1, 'magnification': 1.1, 'name_color': '', 'medal_info': {'target_id': 194484313, 'special': '', 'icon_id': 1000006, 'anchor_uname': '', 'anchor_roomid': 0, 'medal_level': 21, 'medal_name': 'ASAKI', 'medal_color': 1725515, 'medal_color_start': 1725515, 'medal_color_end': 5414290, 'medal_color_border': 1725515, 'is_lighted': 1, 'guard_level': 0}, 'svga_block': 0}}}
@room.on("SEND_GIFT")  # 收到礼物
async def on_gift(msg):
    uid = msg['data']['data']['uid']
    num = msg['data']['data']['num']
    uname = msg['data']['data']['uname']
    giftname = msg['data']['data']['giftName']
    gold = msg['data']['data']['gold']
    silver = msg['data']['data']['silver']
    total_coin = msg['data']['data']['total_coin']
    coin_type = msg['data']['data']['coin_type']
    medal_uid = msg['data']['data']['medal_info']['target_id'] # 带着的粉丝牌所属主播的UID
    medal_level = msg['data']['data']['medal_info']['medal_level'] # 带着的粉丝牌等级
    medal_name = msg['data']['data']['medal_info']['medal_name'] # 带着的粉丝牌名称
    is_lighted = msg['data']['data']['medal_info']['is_lighted'] == 1 # 带着的粉丝牌是否被点亮
    guard_level = msg['data']['data']['medal_info']['guard_level'] # 带着的粉丝牌的大航海等级
    log.info(colored("【收到礼物】" + uname + " 赠送了" + giftname + "x" + str(num), 'magenta'))
    ds.thanks_gift(uname, giftname, num)


# {'room_display_id': 732, 'room_real_id': 6154037, 'type': 'COMBO_SEND', 'data': {'cmd': 'COMBO_SEND', 'data': {'uid': 3822596, 'ruid': 194484313, 'uname': '猫耳☆幻想冰旋', 'r_uname': 'Asaki大人', 'combo_num': 21, 'gift_id': 30607, 'gift_num': 0, 'batch_combo_num': 21, 'gift_name': '小心心', 'action': '投喂', 'combo_id': 'gift:combo_id:3822596:194484313:30607:1612862905.8227', 'batch_combo_id': 'batch:gift:combo_id:3822596:194484313:30607:1612862905.8234', 'is_show': 1, 'send_master': None, 'name_color': '', 'total_num': 21, 'medal_info': {'target_id': 194484313, 'special': '', 'icon_id': 1000006, 'anchor_uname': '', 'anchor_roomid': 0, 'medal_level': 15, 'medal_name': 'ASAKI', 'medal_color': 12478086, 'medal_color_start': 12478086, 'medal_color_end': 12478086, 'medal_color_border': 12478086, 'is_lighted': 1, 'guard_level': 0}, 'combo_total_coin': 0}}}
@room.on("COMBO_SEND")  # 礼物连击
async def on_gift_combo(msg):
    uid = msg['data']['data']['uid'] # 赠送礼物的用户UID
    uname = msg['data']['data']['uname'] # 赠送礼物的用户名
    ruid = msg['data']['data']['ruid'] # 收到礼物的主播UID
    r_uname = msg['data']['data']['r_uname'] # 收到礼物主播的用户名
    giftname = msg['data']['data']['gift_name']
    total_num = msg['data']['data']['total_num']
    medal_uid = msg['data']['data']['medal_info']['target_id'] # 带着的粉丝牌所属主播的UID
    medal_level = msg['data']['data']['medal_info']['medal_level'] # 带着的粉丝牌等级
    medal_name = msg['data']['data']['medal_info']['medal_name'] # 带着的粉丝牌名称
    is_lighted = msg['data']['data']['medal_info']['is_lighted'] == 1 # 带着的粉丝牌是否被点亮
    guard_level = msg['data']['data']['medal_info']['guard_level'] # 带着的粉丝牌的大航海等级
    coin = msg['data']['data']['combo_total_coin']
    log.info(colored("【礼物连击】" + uname + " 赠送了 " + giftname + " x" + str(total_num), 'yellow'))


# {'room_display_id': 732, 'room_real_id': 6154037, 'type': 'GUARD_BUY', 'data': {'cmd': 'GUARD_BUY', 'data': {'uid': 9405475, 'username': '超超超超超超超爱', 'guard_level': 3, 'num': 1, 'price': 198000, 'gift_id': 10003, 'gift_name': '舰长', 'start_time': 1612869234, 'end_time': 1612869234}}}
@room.on("GUARD_BUY")  # 收到大航海
async def on_guard_buy(msg):
    global dahanghai_dict
    uid = msg['data']['data']['uid']
    uname = msg['data']['data']['username']
    guard_level = msg['data']['data']['guard_level']
    num = msg['data']['data']['num']
    price = msg['data']['data']['price']
    giftname = msg['data']['data']['gift_name']

    dahanghai_dict = utils.get_dahanghai_dict(room_id=room_id)  # 刷新大航海表
    log.info(colored(str(uname + ' 赠送了' + str(num) + '个月' + giftname + ' 价值￥' + str(price / 1000)), 'red'))
    ds.thanks_guard(uname, giftname, num)


@room.on("PREPARING")  # 直播结束
async def on_live_end(msg):
    global isStreaming
    log.warning(colored("********************【直播结束】********************", 'red', 'on_yellow'))
    isStreaming = False
    welcomed_list.clear()


# {'room_display_id': 732, 'room_real_id': 6154037, 'type': 'LIVE', 'data': {'cmd': 'LIVE', 'roomid': 6154037}}
@room.on("LIVE")  # 直播开始
async def on_live_on(msg):
    global isStreaming
    log.warning(colored("********************【直播开始】********************", 'red', 'on_yellow'))
    isStreaming = True
    welcomed_list.clear()


# {'room_display_id': 732, 'room_real_id': 6154037, 'type': 'ROOM_REAL_TIME_MESSAGE_UPDATE', 'data': {'cmd': 'ROOM_REAL_TIME_MESSAGE_UPDATE', 'data': {'roomid': 6154037, 'fans': 600657, 'red_notice': -1, 'fans_club': 15463}}}
@room.on("ROOM_REAL_TIME_MESSAGE_UPDATE")  # 粉丝数更新
async def on_fans_update(msg):
    num_fans = msg['data']['data']['fans']
    num_clubs = msg['data']['data']['fans_club']
    log.info(colored("粉丝数更新，最新粉丝数量：" + str(num_fans) + "，粉丝团成员数：" + str(num_clubs), 'yellow'))


@room.on("ALL") # 所有事件均触发，DEBUG时使用，来找到新的或者已修改的事件
async def on_all(msg):
    types = ["ROOM_REAL_TIME_MESSAGE_UPDATE", "LIVE", "COMBO_SEND", "SEND_GIFT", "ENTRY_EFFECT", "INTERACT_WORD", "DANMU_MSG", "NOTICE_MSG", "VIEW"]
    if msg['type'] not in types:
        log.debug(str(msg).replace('%', '') + '\n') # 解决日志无法输出'%'的问题


"""
**************************************************************************
***************************** 定义定时触发任务 *****************************
**************************************************************************
"""


# 每日零点刷新大航海列表
@scheduler.scheduled_job(trigger='cron', id='new_day_job', misfire_grace_time=10, hour='0', minute='0', second='5')
def new_day_job():
    global dahanghai_dict
    log.info(colored("新的一天到来了，执行cleanup任务！", on_color='on_yellow'))
    # 刷新大航海列表字典
    dahanghai_dict = utils.get_dahanghai_dict(room_id=room_id)
    # 刷新图灵机器人API重试次数
    turing.reset_retry_count()


# 发送定时弹幕
@scheduler.scheduled_job(trigger='interval', id='interval_job', minutes=config.getint('DANMAKU', 'SCHEDULED_INTERVAL'))
def interval_job():
    if isStreaming:
        content = random.choice(config.get('DANMAKU', 'SCHEDULED_NOTICE').split(','))
        log.info(colored("定时弹幕已触发：" + content, on_color='on_yellow'))
        ds.send_text(content)


async def console_input():
    """
    用户可以通过控制台与程序交互
    """
    while True:
        input_text = await utils.ainput()
        if input_text == 'r':  # 刷新配置文件
            log.warning(colored("刷新配置文件...", color='blue', attrs=['bold', ]))
            utils.config_check(config, config_path)
        else:  # 发送弹幕
            ds.send_text(input_text)


"""
**************************************************************************
***************************** 主程序入口，启动 *****************************
**************************************************************************
"""

if __name__ == '__main__':
    # 启动控制台可以发送弹幕的功能
    log.warning("在控制台直接输入内容即可发送弹幕！")
    asyncio.get_event_loop().create_task(console_input())
    # 启动定时任务
    scheduler.start()
    # 连接至直播间，并监听事件
    try:
        room.connect()
    except Exception as e:
        log.critical(colored("致命错误：直播间重连失败！即将退出程序，需要手动重启！" + str(e), 'red', 'on_green', ['bold', ]))
    finally:
        os.system("PAUSE")
        sys.exit(0)
