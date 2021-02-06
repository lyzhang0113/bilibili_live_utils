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
    def __init__(self, api_url: str, api_keys: list, request_body: str):
        self.api_url = api_url
        self.api_keys = api_keys
        self.request_body = json.loads(request_body)
        self.log = logging.getLogger('')
        self._current_api = 0
        self._retry_count = 0

    def ask(self, text: str, user_id=str(random.randrange(10000000000, 99999999999))):
        self.log.debug("用户" + user_id + "向AI请求：" + text)
        request_body = self.request_body
        request_body["perception"]["inputText"]["text"] = text
        request_body["userInfo"]["userId"] = user_id
        request_body["userInfo"]["apiKey"] = self.api_keys[self._current_api]

        response = requests.post(self.api_url, json=request_body)
        response = response.json()
        response_code = response["intent"]["code"]

        # 尝试所有API key仍然不行：
        if self._retry_count == len(self.api_keys):
            return "机器人没电啦呜呜~"

        # 如果接口报请求次数限制错误，尝试下一API_KEY
        if str(response_code) == '4003':
            self.log.warning("当前API次数已用完，尝试下一API")
            self._retry_count += 1
            self._current_api = self._current_api + 1 if self._current_api < len(self.api_keys) else 0
            return self.ask(text=text, user_id=user_id)

        response_text = str(response["results"][0]["values"]["text"])
        self.log.info("A:" + response_text + "请求返回码：" + str(response_code))
        self._retry_count = 0
        return response_text

    def refresh_retry_count(self):
        """
        清空重试次数。API调用次数每日更新，即每日零点应触发一次。
        :return:
        """
        self._retry_count = 0
