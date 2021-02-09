#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
:file           turing_ai.py
:project        bilibili_live_utils
:name           图灵机器人工具类
:author         Doby2333
:github         https://github.com/lyzhang0113/bilibili-live-utils
:version        0.1.0
:created        2021/01/31 22:04
:description
"""

import requests
import json
import random
import logging


class TuringAI(object):
    def __init__(self, api_url: str, api_keys: list, request_body: str, enable: bool = True):
        """
        初始化图灵机器人
        :param api_url: 图灵机器人的API接口地址
        :param api_keys: 包含一个或多个API KEY的list
        :param request_body: 请求体模板
        """
        self.api_url = api_url
        self.api_keys = api_keys
        self.request_body = json.loads(request_body)
        self.enable = enable
        self.log = logging.getLogger('bilibili_live_utils')
        self._current_api = 0
        self._retry_count = 0

    def ask(self, text: str, user_id=str(random.randrange(10000000000, 99999999999))):
        """
        向图灵机器人API发送请求
        :param text: 要发送的内容
        :param user_id: 用户id（用来区分对话，使弹幕发送者可以和机器人上下文联系对话）
        :return: 图灵机器人的回复
        :raise ConnectionError: 当所有API KEY次数均用尽时抛出
        """
        if not self.enable:
            return
        self.log.debug("用户" + user_id + "向图灵AI请求：" + text)
        request_body = self.request_body
        request_body['perception']['inputText']['text'] = text
        request_body['userInfo']['userId'] = user_id
        api_key = self.api_keys[self._current_api]
        request_body['userInfo']['apiKey'] = api_key

        self.log.debug("使用API_KEY = " + api_key)
        response = requests.post(self.api_url, json=request_body).json()
        self.log.debug("图灵API返回：" + response)
        response_code = response['intent']['code']

        # 尝试所有API key仍然不行：
        if self._retry_count >= len(self.api_keys):
            raise ConnectionError("所有API KEY均失效")

        # 如果接口报请求次数限制错误，尝试下一API_KEY
        if str(response_code) == '4003':
            self.log.warning("当前API_KEY次数已用完，尝试下一个API_KEY")
            self._retry_count += 1
            self._current_api = self._current_api + 1 if self._current_api < len(self.api_keys) else 0
            return self.ask(text=text, user_id=user_id)

        response_text = str(response['results'][0]['values']['text'])
        self._retry_count = 0
        return response_text

    def reset_retry_count(self):
        """
        清空重试次数。API调用次数每日更新，即每日零点应触发一次。
        :return: None
        """
        self._retry_count = 0
