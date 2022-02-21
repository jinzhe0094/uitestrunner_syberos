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

import pkg_resources
import paramiko  # 用于调用scp命令
from scp import SCPClient

print('hello')
sop_name = "data/server.sop"
if pkg_resources.resource_exists(__name__, sop_name):
    sop = pkg_resources.resource_stream(__name__, sop_name)
    f = open("./server.sop", "wb")
    f.write(sop.read())
    f.close()

    host = "192.168.100.100"
    port = 22
    username = "developer"
    password = "system"

    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    ssh_client.connect(host, port, username, password)
    scp_client = SCPClient(ssh_client.get_transport(), socket_timeout=15.0)
    scp_client.put("./server.sop", "/tmp/")

    print("push guiAutoTest_support to device and launch it")
    ssh_client.exec_command("ins-tool -iu /tmp/server.sop && dbus-send --system --print-reply --dest=com.syberos.iomanager /com/syberos/compositor/IOManager com.syberos.compositor.IOManager.sendAppData string:\"$(echo -e \"PowerLaunchRunApp\t0\tcom.syberos.guiAutoTest_support\tguiAutoTest_support\t\")\"")

    ssh_client.close()
