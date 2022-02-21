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

import base64
import os
import platform
import re
import threading
import ctypes
from ctypes import *
from subprocess import *
from .selenium_phantomjs.webdriver.remote import webdriver
from .Item import Item
from .Connection import Connection
from .Events import Events
import configparser
from multiprocessing import Process, Pipe
from .Watcher import *
import psutil
import warnings
from .DataStruct import *


def _watcher_process(main_pid, host, port, conn):
    device = Device(host=host, port=port, _main=False)
    WatchWorker(device, conn, main_pid).run()


def _start_watcher(host, port, watcher_conn):
    watcher_process = Process(target=_watcher_process, args=(os.getpid(), host, port, watcher_conn))
    watcher_process.daemon = True
    watcher_process.start()


def _web_driver_daemon(main_pid, wb_pid, parent_pid):
    psutil.Process(parent_pid).kill()
    main_process = psutil.Process(main_pid)
    wb_process = psutil.Process(wb_pid)
    while main_process.is_running():
        time.sleep(3)
    if wb_process.is_running():
        wb_process.kill()
    exit(0)


def _create_orphan_thread(main_pid, wb_pid):
    wb_daemon_process = Process(target=_web_driver_daemon, args=(main_pid, wb_pid, os.getpid()))
    wb_daemon_process.daemon = False
    wb_daemon_process.start()


def _start_web_driver_daemon(wb_pid):
    orphan_thread = Process(target=_create_orphan_thread, args=(os.getpid(), wb_pid))
    orphan_thread.daemon = False
    orphan_thread.start()


class Device(Events):
    """
    Device初始化，获取设备初始信息，创建相关子线程与子进程等。\n
    :param host: 设备通信IP地址(默认为192.168.100.100)
    :param port: 设备通信端口(默认为10008，一般不需修改)
    :param _main: 主进程标识符(禁止用户使用)
    :ivar xml_string: 储存最后一次的设备UI布局信息xml字符串
    :ivar default_timeout: 框架整体的默认超时时间
    :ivar control_host_type: 控制端平台类型，枚举类型Controller
    """
    con = Connection()
    __os_version = ""
    __serial_number = ""
    xml_string = ""
    __xpath_file = "./xpath_list.ini"
    __screenshots = "./screenshots/"
    default_timeout = 30
    __syslog_output = False
    __syslog_output_keyword = ""
    __syslog_save = False
    __syslog_save_path = "./syslog/"
    __syslog_save_name = ""
    __syslog_save_keyword = ""
    watcher_list = []
    __main_conn, __watcher_conn = Pipe()
    __width = 0
    __height = 0
    __syslog_tid = None
    control_host_type = Controller.ANYWHERE

    def __init__(self, host="192.168.100.100", port=10008, _main=True):
        super().__init__(d=self)
        warnings.simplefilter('ignore', ResourceWarning)
        self.con.host = host
        self.con.port = port
        self.con.connect()
        self.__path = os.path.realpath(__file__).split(os.path.basename(__file__))[0]
        self.__serial_number = str(self.con.get(path="getSerialNumber").read(), 'utf-8')
        self.__os_version = str(self.con.get(path="getOsVersion").read(), 'utf-8')
        self.__set_display_size()
        if _main:
            self.__check_platform()
            if self.control_host_type != Controller.ANYWHERE:
                if self.control_host_type != Controller.WINDOWS_AMD64:
                    _start_web_driver_daemon(self.__wb_process.pid)
                _start_watcher(host, port, self.__watcher_conn)
            syslog_thread = threading.Thread(target=self.__logger)
            syslog_thread.daemon = True
            syslog_thread.start()
        self.refresh_layout()
        if self.control_host_type != 0:
            self.webdriver = webdriver.WebDriver(command_executor='http://127.0.0.1:8910/wd/hub')

    def __check_platform(self):
        p = platform.system()
        m = platform.machine()
        if p == "Windows" and m == "AMD64":
            self.control_host_type = Controller.WINDOWS_AMD64
            self.__init_webdriver("win32_x86_64_phantomjs", "libsimulation-rendering.dll")
        elif p == "Linux" and m == "x86_64":
            self.control_host_type = Controller.LINUX_X86_64
            self.__init_webdriver("linux_x86_64_phantomjs", "libsimulation-rendering.so")
        elif p == "Darwin" and m == "x86_64":
            self.control_host_type = Controller.DARWIN_X86_64
            self.__init_webdriver("darwin_x86_64_phantomjs", "libsimulation-rendering.dylib")

    def __init_webdriver(self, p_name, l_name):
        self.__wb_process = Popen([self.__path + "data/" + p_name,
                                   self.__path + "data/ghostdriver/main.js",
                                   str(self.__width), str(self.__height)], stdout=PIPE, stderr=PIPE)
        for i in range(2):
            self.__wb_process.stdout.readline()
        ll = cdll.LoadLibrary
        self.libsr = ll(self.__path + "data/" + l_name)
        self.libsr.go.restype = ctypes.c_char_p

    def push_watcher_data(self):
        self.__main_conn.send({'watcher_list': self.watcher_list})

    def watcher(self, name: str) -> Watcher:
        """
        创建一个待启动的监视者，可以根据指定条件作出相应反应。\n
        :param name: 标识名称，不可重复
        :return: 返回一个实例化的Watcher对象
        """
        w = Watcher({'name': name}, self)
        return w

    def start_watcher(self, name: str) -> None:
        """
        启动一个已有的监视者。\n
        :param name: 监视者标识名称
        :return: 无
        """
        for watcher in self.watcher_list:
            if name == watcher['name']:
                watcher['is_run'] = True
        self.__main_conn.send({'watcher_list': self.watcher_list})

    def pause_watcher(self, name: str) -> None:
        """
        暂停一个已有的监视者。\n
        :param name: 监视者标识名称
        :return: 无
        """
        for watcher in self.watcher_list:
            if name == watcher['name']:
                watcher['is_run'] = False
        self.__main_conn.send({'watcher_list': self.watcher_list})

    def delete_watcher(self, name: str) -> None:
        """
        删除一个已有的监视者。\n
        :param name: 监视者标识名称
        :return: 无
        """
        for watcher in self.watcher_list:
            if name == watcher['name']:
                self.watcher_list.remove(watcher)
        self.__main_conn.send({'watcher_list': self.watcher_list})

    def __logger_pingpong(self):
        self.con.get(path="SSEPingpong", args="tid=" + str(self.__syslog_tid))
        threading.Timer(5, self.__logger_pingpong).start()

    def __logger(self):
        syslog_save_path = ""
        syslog_file = None
        first = True
        messages = self.device.con.sse("SysLogger")
        for msg in messages:
            log_str = str(msg.data)
            if first:
                self.__syslog_tid = log_str
                threading.Timer(5, self.__logger_pingpong).start()
                first = False
            if self.__syslog_output and re.search(self.__syslog_output_keyword, log_str):
                print(log_str)
            if self.__syslog_save and re.search(self.__syslog_save_keyword, log_str):
                if syslog_save_path != self.__syslog_save_path + "/" + self.__syslog_save_name:
                    syslog_save_path = self.__syslog_save_path + "/" + self.__syslog_save_name
                    if not os.path.exists(self.__syslog_save_path):
                        os.makedirs(self.__syslog_save_path)
                    syslog_file = open(syslog_save_path, 'w')
                syslog_file.write(log_str + "\n")
                syslog_file.flush()

    def set_syslog_output(self, is_enable: bool, keyword: str = "") -> None:
        """
        设置设备log输出(打印至控制端标准输出stdout)开关。\n
        :param is_enable: log输出开关, bool值, True为开启，False为关闭
        :param keyword: 筛选关键字(筛选最小单位行)，如果为空则全部打印
        :return: 无
        """
        self.__syslog_output_keyword = keyword
        self.__syslog_output = is_enable

    def syslog_output(self) -> bool:
        """
        获取设备log输出开关状态。\n
        :return: log输出开关, bool值, True为开启，False为关闭
        """
        return self.__syslog_output

    def syslog_output_keyword(self) -> str:
        """
        查询当前设备log输出时的筛选关键字。\n
        :return: 关键字字符串
        """
        return self.__syslog_output_keyword

    def set_syslog_save_start(self, save_path: str = "./syslog/", save_name: str = None,
                              save_keyword: str = "") -> None:
        """
        设置保存设备log开始。\n
        :param save_path: 保存文件路径，指定一个文件夹的相对或绝对路径，默认在当前工作目录下的syslog文件夹
        :param save_name: log文件保存名称，默认以时间戳命名
        :param save_keyword: 筛选关键字(筛选最小单位行)，如果为空则全部保存
        :return: 无
        """
        self.__syslog_save_path = save_path
        if save_name is None:
            current_remote_time = self.con.get(path="getSystemTime").read()
            self.__syslog_save_name = str(current_remote_time, 'utf-8') + ".log"
        self.__syslog_save_keyword = save_keyword
        self.__syslog_save = True

    def set_syslog_save_stop(self) -> None:
        """
        停止保存设备log，如果不调用此方法则会一直保存至进程结束。\n
        :return: 无
        """
        self.__syslog_save = False

    def syslog_save(self) -> bool:
        """
        获取当前是否正在保存设备log。\n
        :return: bool值，True为正在保存中，False则相反
        """
        return self.__syslog_save

    def syslog_save_path(self) -> str:
        """
        获取当前设备log保存目录。\n
        :return: 路径字符串
        """
        return self.__syslog_save_path

    def syslog_save_name(self) -> str:
        """
        获取当前设备log保存名称。\n
        :return: 名称字符串
        """
        return self.__syslog_save_name

    def syslog_save_keyword(self) -> str:
        """
        获取当前设备log保存筛选关键字。\n
        :return: 关键字字符串
        """
        return self.__syslog_save_keyword

    def set_default_timeout(self, timeout: int) -> None:
        """
        设置当前框架默认超时时间(默认为30秒)。\n
        :param timeout: 超时时间(单位:秒)
        :return: 无
        """
        self.default_timeout = timeout

    def set_xpath_list(self, path: str) -> None:
        """
        设置存放xpath信息的ini文件路径(默认为当前工作目录下的xpath_list.ini)。\n
        :param path: 文件路径
        :return: 无
        """
        self.__xpath_file = path

    def set_screenshots_path(self, path: str) -> None:
        """
        设置存放系统截图的文件夹路径(默认为当前工作目录下的screenshots文件夹)。\n
        :param path: 文件夹路径
        :return: 无
        """
        self.__screenshots = path

    def screenshot(self, path: str = __screenshots) -> str:
        """
        获取设备当前屏幕截图。\n
        :param path: 截图存放路径(默认为前工作目录下的screenshots文件夹或者用户通过Device.set_screenshots_path(path: str)接口设置的路径)
        :return: 截图名称
        """
        if not os.path.exists(path):
            os.makedirs(path)
        img_base64 = str(self.con.get(path="getScreenShot").read(), 'utf-8').split(',')[0]
        current_remote_time = self.con.get(path="getSystemTime").read()
        file_name = str(current_remote_time, 'utf-8') + ".png"
        image = open(path + "/" + file_name, "wb")
        image.write(base64.b64decode(img_base64))
        image.close()
        return file_name

    def grab_image_to_base64(self, cx: int, cy: int, width: int, height: int, rotation: int = 0,
                             scale: float = 1) -> str:
        """
        获取指定位置、大小及状态的范围截图。\n
        :param cx: 范围旋转缩放前的中心点横坐标
        :param cy: 范围旋转缩放前的中心点纵坐标
        :param width: 范围旋转缩放前的宽度
        :param height: 范围旋转缩放前的高度
        :param rotation: 顺时针旋转角度
        :param scale: 缩放系数
        :return: 截图的base64形态
        """
        return str(self.con.get(path="grabImage", args="x=" + str(round(cx))
                                                       + "&y=" + str(round(cy))
                                                       + "&w=" + str(round(width))
                                                       + "&h=" + str(round(height))
                                                       + "&r=" + str(round(rotation))
                                                       + "&s=" + str(round(scale))).read(), 'utf-8')

    def __set_display_size(self):
        image_data = str(self.con.get(path="getScreenShot").read(), 'utf-8')
        self.__height = int(image_data.split(",")[1])
        self.__width = int(image_data.split(",")[2])

    def display_width(self) -> int:
        """
        获取当前设备屏幕宽度。\n
        :return: 屏幕宽度像素数int值
        """
        return self.__width

    def display_height(self) -> int:
        """
        获取当前设备屏幕高度。\n
        :return: 屏幕高度像素数int值
        """
        return self.__height

    def get_xpath(self, sop_id: str, key: str) -> str:
        """
        通过sopid与key在xpath信息ini文件中查询xpath值。\n
        :param sop_id: 设备应用的sopid
        :param key: 键
        :return: xpath值字符串
        """
        if not os.path.exists(self.__xpath_file):
            f = open(self.__xpath_file, "w")
            f.close()
        conf = configparser.ConfigParser()
        conf.read(self.__xpath_file)
        return conf.get(sop_id, key)

    def refresh_layout(self) -> None:
        """
        刷新当前设备的UI布局信息。\n
        :return: 无
        """
        self.xml_string = str(self.con.get(path="getLayoutXML").read(), 'utf-8')

    def os_version(self) -> str:
        """
        获取SyberOS系统版本。\n
        :return: 系统版本字符串
        """
        return self.__os_version

    def serial_number(self) -> str:
        """
        获取当前设备硬件序列号。\n
        :return: 序列号字符串
        """
        return self.__serial_number

    def find_item_by_xpath_key(self, sopid: str, xpath_key: str) -> Item:
        """
        获取元素控件实例化对象。\n
        :param sopid: 设备应用的sopid
        :param xpath_key: xpath信息ini文件中的键
        :return: Item对象
        """
        i = Item(d=self, s=sopid, xpath=self.get_xpath(sopid, xpath_key))
        return i

    def find_item_by_xpath(self, sopid: str, xpath: str) -> Item:
        """
        获取元素控件实例化对象。\n
        :param sopid: 设备应用的sopid
        :param xpath: xpath值字符串
        :return: Item对象
        """
        i = Item(d=self, s=sopid, xpath=xpath)
        return i
