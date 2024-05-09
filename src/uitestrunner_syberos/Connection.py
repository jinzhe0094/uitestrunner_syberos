# Copyright (C) <2021>  YUANXIN INFORMATION TECHNOLOGY GROUP CO.LTD and Jinzhe Wang
# This file is part of uitestrunner_syberos
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import http.client
import urllib.request
from time import sleep

from sseclient import SSEClient


class Connection:

    def __init__(self, host: str = None, port: int = None, d=None):
        self.host = host
        self.port = port
        self.device = d
        self.default_timeout = self.device.default_timeout

    def connect(self):
        for i in range(11):
            try:
                request = urllib.request.Request("http://" + self.host + ":" + str(self.port))
                reply = urllib.request.urlopen(request, timeout=self.default_timeout)
                if i > 0:
                    print("重试成功。")
                if reply.status == 200:
                    return True
            except Exception as e:
                if i > 0:
                    print("第" + str(i) + "次重试失败！")
                else:
                    print("设备连接失败！")
                print("失败信息：" + str(e))
                if i < 10:
                    print("即将进行第" + str(i + 1) + "/10次重试，5秒后开始：")
                    for j in range(5):
                        print("......" + str(5 - j))
                        sleep(1)
                    print("开始重试。")
        return False

    def get(self, path, args="", headers=None, timeout=None):
        if headers is None:
            headers = {'Accept': 'text/plain; charset=UTF-8'}
        if not timeout:
            timeout = self.default_timeout
        try:
            request = urllib.request.Request(url="http://" + self.host + ":" + str(self.port) + "/" + path + "?" + args,
                                             headers=headers, method="GET")
            reply = urllib.request.urlopen(request, timeout=timeout)
        except http.client.BadStatusLine:
            request = urllib.request.Request(url="http://" + self.host + ":" + str(self.port) + "/" + path + "?" + args,
                                             headers=headers, method="GET")
            reply = urllib.request.urlopen(request, timeout=timeout)
        return reply

    def post(self, path, data=None, headers=None, timeout=None):
        if not timeout:
            timeout = self.default_timeout
        request = urllib.request.Request(url="http://" + self.host + ":" + str(self.port) + "/" + path, data=data,
                                         headers=headers, method="POST")
        reply = urllib.request.urlopen(request, timeout=timeout)
        return reply

    def sse(self, path):
        messages = SSEClient(url="http://" + self.host + ":" + str(self.port) + "/" + path)
        return messages
