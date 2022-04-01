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
import socket
import time
import urllib.request
import urllib.error
import pkg_resources
import paramiko
from scp import SCPClient
import threading


wait = False
host = "192.168.100.100"
port = 22
username = "developer"
password = "system"
ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
ssh_client.connect(host, port, username, password)
scp_client = SCPClient(ssh_client.get_transport(), socket_timeout=15.0)
result = False


def print_message(msg, tabs):
    global wait
    i = 7
    while wait:
        time.sleep(0.2)
        j = i % 7
        if j == 0:
            print('\r\033[1;36m' + msg + '\033[0m' + tabs + '\033[1;33m[.     ]\033[0m', end='', flush=True)
        elif j == 1:
            print('\r\033[1;36m' + msg + '\033[0m' + tabs + '\033[1;33m[..    ]\033[0m', end='', flush=True)
        elif j == 2:
            print('\r\033[1;36m' + msg + '\033[0m' + tabs + '\033[1;33m[...   ]\033[0m', end='', flush=True)
        elif j == 3:
            print('\r\033[1;36m' + msg + '\033[0m' + tabs + '\033[1;33m[....  ]\033[0m', end='', flush=True)
        elif j == 4:
            print('\r\033[1;36m' + msg + '\033[0m' + tabs + '\033[1;33m[..... ]\033[0m', end='', flush=True)
        elif j == 5:
            print('\r\033[1;36m' + msg + '\033[0m' + tabs + '\033[1;33m[......]\033[0m', end='', flush=True)
        else:
            print('\r\033[1;36m' + msg + '\033[0m' + tabs + '\033[1;33m[      ]\033[0m', end='', flush=True)
        i += 1


def worker(step):
    global wait
    global result
    wait = True
    result = False
    if step == 1:
        sop = pkg_resources.resource_stream(__name__, sop_name)
        f = open("./server.sop", "wb")
        f.write(sop.read())
        f.close()
    elif step == 2:
        scp_client.put("./server.sop", "/tmp/")
        stdin, stdout, stderr = ssh_client.exec_command("ls -l /tmp/server.sop")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0 and not stdout.read().decode() == "":
            result = True
    elif step == 3:
        stdin, stdout, stderr = ssh_client.exec_command("ins-tool -iu /tmp/server.sop")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            stdin, stdout, stderr = ssh_client.exec_command("dbus-send --system --print-reply --"
                                                            "dest=com.syberos.packageserviced /c"
                                                            "om/syberos/packageserviced com.sybe"
                                                            "ros.packageserviced.Interface.isIns"
                                                            "talled string:com.syberos.guiAutoTe"
                                                            "st_support")
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0 and stdout.read().decode().split('\n')[1].split('boolean')[1].split(' ')[1] == "true":
                result = True
    elif step == 4:
        stdin, stdout, stderr = ssh_client.exec_command("dbus-send --system --print-reply --dest"
                                                        "=com.syberos.compositor /com/syberos/co"
                                                        "mpositor com.syberos.compositor.GuiAuto"
                                                        "TestInterfacePre.setGuiAutoTestSwitch b"
                                                        "oolean:true")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            stdin, stdout, stderr = ssh_client.exec_command("dbus-send --system --print-reply --"
                                                            "dest=com.syberos.compositor /com/sy"
                                                            "beros/compositor com.syberos.compos"
                                                            "itor.GuiAutoTestInterfacePre.getGui"
                                                            "AutoTestSwitch")
            if exit_status == 0 and stdout.read().decode().split('\n')[1].split('boolean')[1].split(' ')[1] == "true":
                result = True
    elif step == 5:
        stdin, stdout, stderr = ssh_client.exec_command("echo system | su root -c 'killall system-main'")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            die_time = int(time.time()) + 30
            while True:
                stdin, stdout, stderr = ssh_client.exec_command("dbus-send --system --print-reply --"
                                                                "dest=com.syberos.compositor /com/sy"
                                                                "beros/compositor com.syberos.compos"
                                                                "itor.GuiAutoTestInterface.getTopWin"
                                                                "dowPid")
                exit_status = stdout.channel.recv_exit_status()
                if exit_status == 0:
                    result = True
                    break
                time.sleep(0.5)
                if int(time.time()) > die_time:
                    break
    elif step == 6:
        die_time = int(time.time()) + 30
        while True:
            try:
                request = urllib.request.Request("http://192.168.100.100:10008")
                reply = urllib.request.urlopen(request, timeout=30)
                if reply.status == 200:
                    result = True
                    break
            except urllib.error.ContentTooShortError:
                pass
            except urllib.error.URLError:
                pass
            except socket.timeout:
                pass
            time.sleep(0.5)
            if int(time.time()) > die_time:
                break
    wait = False


print('\033[1mWelcome to use gui auto test framework for SyberOS.(1.1.0)\033[0m')
sop_name = "data/server.sop"
if pkg_resources.resource_exists(__name__, sop_name):
    syslog_thread = threading.Thread(target=worker, daemon=True, args=(1,))
    syslog_thread.start()
    print_message('01.Generate installation package.', '\t\t')
    print('\r\033[1;36m01.Generate installation package.\033[0m\t\t\033[1;32m[  OK  ]\033[0m', flush=True)

    syslog_thread = threading.Thread(target=worker, daemon=True, args=(2,))
    syslog_thread.start()
    print_message('02.Push guiAutoTest_support.', '\t\t\t')
    if result:
        print('\r\033[1;36m02.Push guiAutoTest_support.\033[0m\t\t\t\033[1;32m[  OK  ]\033[0m', flush=True)
    else:
        print('\r\033[1;36m02.Push guiAutoTest_support.\033[0m\t\t\t\033[1;31m[Failed]\033[0m', flush=True)
        exit()

    syslog_thread = threading.Thread(target=worker, daemon=True, args=(3,))
    syslog_thread.start()
    print_message('03.Install guiAutoTest_support.', '\t\t\t')
    if result:
        print('\r\033[1;36m03.Install guiAutoTest_support.\033[0m\t\t\t\033[1;32m[  OK  ]\033[0m', flush=True)
    else:
        print('\r\033[1;36m03.Install guiAutoTest_support.\033[0m\t\t\t\033[1;31m[Failed]\033[0m', flush=True)
        exit()

    syslog_thread = threading.Thread(target=worker, daemon=True, args=(4,))
    syslog_thread.start()
    print_message('04.Open the switch with gui auto test.', '\t\t')
    if result:
        print('\r\033[1;36m04.Open the switch with gui auto test.\033[0m\t\t\033[1;32m[  OK  ]\033[0m', flush=True)
    else:
        print('\r\033[1;36m04.Open the switch with gui auto test.\033[0m\t\t\033[1;31m[Failed]\033[0m', flush=True)
        exit()

    syslog_thread = threading.Thread(target=worker, daemon=True, args=(5,))
    syslog_thread.start()
    print_message('05.Restart system-main.', '\t\t\t\t')
    if result:
        print('\r\033[1;36m05.Restart system-main.\033[0m\t\t\t\t\033[1;32m[  OK  ]\033[0m', flush=True)
    else:
        print('\r\033[1;36m05.Restart system-main.\033[0m\t\t\t\t\033[1;31m[Failed]\033[0m', flush=True)
        exit()

    syslog_thread = threading.Thread(target=worker, daemon=True, args=(6,))
    syslog_thread.start()
    print_message('06.Check http server interface.', '\t\t\t')
    if result:
        print('\r\033[1;36m06.Check http server interface.\033[0m\t\t\t\033[1;32m[  OK  ]\033[0m', flush=True)
    else:
        print('\r\033[1;36m06.Check http server interface.\033[0m\t\t\t\033[1;31m[Failed]\033[0m', flush=True)
        exit()


print('\033[1;32mTest support service deployment and launch is successful.\033[0m')
ssh_client.close()

