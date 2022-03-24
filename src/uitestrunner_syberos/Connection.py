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
from sseclient import SSEClient


class Connection:

    def __init__(self, host: str = None, port: int = None, d=None):
        self.host = host
        self.port = port
        self.device = d
        self.default_timeout = self.device.default_timeout

    def connect(self):
        request = urllib.request.Request("http://" + self.host + ":" + str(self.port))
        reply = urllib.request.urlopen(request, timeout=self.default_timeout)
        if reply.status == 200:
            return True
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
            print("BadStatusLine")
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
