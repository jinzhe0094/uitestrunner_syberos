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
import io
import platform
import re
import socket
import sys
import threading
import ctypes
from ctypes import *
from subprocess import *
from .Item import Item
from .Connection import Connection
from .Events import *
import configparser
from multiprocessing import Process, Pipe, Queue
from .Watcher import *
import psutil
import warnings
from .TextItemFromOcr import *
import easyocr
from PIL import Image
from typing import List
import ocrCraftModel4uts
import ocrLangModel4uts
import shutil
from pathlib import Path
import requests
import json
from urllib.parse import quote_plus


main_conn, watcher_conn = Pipe()
watcher_xml_queue = Queue()
mp_queue = Queue()
pm_queue = Queue()
watcher_xml_queue.cancel_join_thread()
watcher_process_list = []
phantomjs_port = 0


def get_free_port():
    """
    获取一个可用的空闲端口
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def _watcher_process(main_pid, host, port, conn, xml_queue, wd_port):
    device = Device(host=host, port=port, _main=False, _xml_queue=xml_queue, _wd_port=wd_port)
    WatchWorker(device, conn, main_pid).run()


def _start_watcher(host, port, w_conn, w_xml_queue, wd_port):
    watcher_process = Process(target=_watcher_process, args=(os.getpid(), host, port, w_conn, w_xml_queue, wd_port))
    watcher_process.daemon = True
    watcher_process.start()


def __restart_phantomjs(wb_pid, pm_q, pt_q, ph_name):
    psutil.Process(wb_pid).kill()
    port = get_free_port()
    wp = Popen([os.path.realpath(__file__).split(os.path.basename(__file__))[0] + "data/" + ph_name,
                "--webdriver=" + str(port)], stdout=PIPE, stderr=PIPE)
    wp.stdout.readline()
    pt_q.put({'wb_pid': wp.pid})
    pm_q.put({'wb_port': port, 'wb_pid': wp.pid})


def _web_driver_daemon(main_pid, wb_pid, parent_pid, pm_q, mp_q, ph_name):
    psutil.Process(parent_pid).kill()
    tp_queue = Queue()
    webdriver_pid = wb_pid
    timer = threading.Timer(60, __restart_phantomjs, [webdriver_pid, pm_q, tp_queue, ph_name])
    while True:
        while not tp_queue.empty():
            data = tp_queue.get()
            webdriver_pid = data['wb_pid']
            timer.cancel()
            timer = threading.Timer(60, __restart_phantomjs, [webdriver_pid, pm_q, tp_queue, ph_name])
        while not mp_q.empty():
            data = mp_q.get()
            if data['type'] == 1:
                timer.cancel()
                timer = threading.Timer(60, __restart_phantomjs, [webdriver_pid, pm_q, tp_queue, ph_name])
                timer.start()
            elif data['type'] == 0:
                timer.cancel()
        if not psutil.Process(main_pid).is_running():
            if psutil.Process(webdriver_pid).is_running():
                psutil.Process(webdriver_pid).kill()
            break
        sleep(0.1)
    exit(0)


def _create_orphan_thread(main_pid, wb_pid, pm_q, mp_q, ph_name):
    wb_daemon_process = Process(target=_web_driver_daemon, args=(main_pid, wb_pid, os.getpid(), pm_q, mp_q, ph_name))
    wb_daemon_process.daemon = False
    wb_daemon_process.start()


def _start_web_driver_daemon(wb_pid, pm_q, mp_q, ph_name):
    orphan_thread = Process(target=_create_orphan_thread, args=(os.getpid(), wb_pid, pm_q, mp_q, ph_name))
    orphan_thread.daemon = False
    orphan_thread.start()


def _init_ocr_models(p: str):
    if not Path(p).exists():
        os.mkdir(p)
    else:
        if not Path(p).is_dir():
            os.remove(p[:-1])
            os.mkdir(p)
        else:
            if Path(p + "finish").exists():
                return
            else:
                shutil.rmtree(p, ignore_errors=True)
                os.mkdir(p)
    for mod in os.listdir(ocrCraftModel4uts.get_path()):
        if not Path(ocrCraftModel4uts.get_path() + mod).is_dir():
            if not Path(p + mod).exists():
                shutil.copy(ocrCraftModel4uts.get_path() + mod, p)
    for mod in os.listdir(ocrLangModel4uts.get_path()):
        if not Path(ocrLangModel4uts.get_path() + mod).is_dir():
            if not Path(p + mod).exists():
                shutil.copy(ocrLangModel4uts.get_path() + mod, p)
    Path(p + "finish").touch()


class Device(Events):
    """
    Device初始化，获取设备初始信息，创建相关子线程与子进程等。\n
    :param host: 设备通信IP地址(默认为192.168.100.100)
    :param port: 设备通信端口(默认为10008，一般不需修改)
    :param syslog_enable: 是否开启syslog(默认为关闭状态，不可中途修改)
    :param _main: 主进程标识符(禁止用户使用)
    :ivar xml_string: 储存最后一次的设备UI布局信息xml字符串
    :ivar default_timeout: 框架整体的默认超时时间
    :ivar control_host_type: 控制端平台类型，枚举类型Controller
    """

    def __init__(self, host: str = None, port: int = None, syslog_enable: bool = False, _main: bool = True, _xml_queue=None, _wd_port: int = 0):
        super().__init__(d=self)
        warnings.simplefilter('ignore', ResourceWarning)
        self.xml_string = ""
        self.__xml_time = time.time()
        self.__xpath_file = sys.path[0] + "/xpath_list.ini"
        self.__environment_file = sys.path[0] + "/environment.ini"
        self.__screenshots = sys.path[0] + "/screenshots/"
        self.__syslog_output = False
        self.__syslog_output_keyword = ""
        self.__syslog_save = False
        self.__syslog_save_path = sys.path[0] + "/syslog/"
        self.__syslog_save_name = ""
        self.__syslog_save_keyword = ""
        self.__phantomjs_name = ""
        self.__lib_name = ""
        self.__width = 0
        self.__height = 0
        self.control_host_type = Controller.ANYWHERE
        self.__ocr_mods = str(Path.home()) + "/.ocr_models/"
        self.__host = "192.168.100.100"
        self.__port = 10008
        if _xml_queue is not None:
            self.__xml_queue = _xml_queue
        if self.has_environment("HOST"):
            self.__host = self.get_environment("HOST")
        if self.has_environment("PORT"):
            self.__port = int(self.get_environment("PORT"))
        if self.has_environment("TIMEOUT"):
            self.default_timeout = int(self.get_environment("TIMEOUT"))
        else:
            self.default_timeout = 60
        if host is not None:
            self.__host = host
        if port is not None:
            self.__port = port
        self.__ocr_server = None
        if self.has_environment("OCR_SERVER"):
            self.__ocr_server = self.get_environment("OCR_SERVER")
        self.__support_device_server = None
        if self.has_environment("SUPPORT_DEVICE_SERVER"):
            self.__support_device_server = self.get_environment("SUPPORT_DEVICE_SERVER")
        self.con = Connection(self.__host, self.__port, self)
        self.con.connect()
        self.__path = os.path.realpath(__file__).split(os.path.basename(__file__))[0]
        self.__serial_number = str(self.con.get(path="getSerialNumber").read(), 'utf-8')
        self.__os_version = str(self.con.get(path="getOsVersion").read(), 'utf-8')
        self.__set_display_size()
        self.is_main = _main
        self.__wd_pid = 0
        self.wd_port = 0
        self.__check_platform()
        if self.wd_port == 0:
            self.wd_port = _wd_port
        if self.is_main:
            if self.control_host_type != Controller.ANYWHERE:
                if self.control_host_type != Controller.WINDOWS_AMD64:
                    if self.__wd_pid != 0:
                        _start_web_driver_daemon(self.__wd_pid, pm_queue, mp_queue, self.__phantomjs_name)
                if self.__host + '_' + str(self.__port) not in watcher_process_list:
                    watcher_process_list.append(self.__host + '_' + str(self.__port))
                    _start_watcher(host, port, watcher_conn, watcher_xml_queue, self.wd_port)
            if syslog_enable:
                syslog_thread = threading.Thread(target=self.__logger)
                syslog_thread.daemon = True
                syslog_thread.start()
            if not self.__ocr_server:
                _init_ocr_models(self.__ocr_mods)
        if self.control_host_type != Controller.ANYWHERE:
            self.webdriver = webdriver.WebDriver(command_executor='http://127.0.0.1:' + str(self.wd_port) + '/wd/hub')
        self.refresh_layout()

    def conn_phantomjs_before(self):
        while not pm_queue.empty():
            data = pm_queue.get()
            self.__wd_pid = data['wb_pid']
            global phantomjs_port
            phantomjs_port = data['wd_port']
            self.wd_port = phantomjs_port
            self.webdriver = webdriver.WebDriver(command_executor='http://127.0.0.1:' + str(self.wd_port) + '/wd/hub')
            main_conn.send({
                'action': 'update_wd_port',
                'port': self.wd_port
            })
        mp_queue.put({'type': 1})

    @staticmethod
    def conn_phantomjs_after():
        mp_queue.put({'type': 0})

    def __check_platform(self):
        p = platform.system()
        m = platform.machine()
        if p == "Windows" and m == "AMD64":
            self.control_host_type = Controller.WINDOWS_AMD64
            self.__phantomjs_name = "win32_x86_64_phantomjs"
            self.__lib_name = "libsimulation-rendering.dll"
        elif p == "Linux" and m == "x86_64":
            self.control_host_type = Controller.LINUX_X86_64
            self.__phantomjs_name = "linux_x86_64_phantomjs"
            self.__lib_name = "libsimulation-rendering.so"
        elif p == "Darwin" and m == "x86_64":
            self.control_host_type = Controller.DARWIN_X86_64
            self.__phantomjs_name = "darwin_x86_64_phantomjs"
            self.__lib_name = "libsimulation-rendering.dylib"
        elif p == "Darwin" and m == "arm64":
            self.control_host_type = Controller.DARWIN_ARM64
            self.__phantomjs_name = "darwin_x86_64_phantomjs"
            self.__lib_name = "libsimulation-rendering-arm64.dylib"
        self.__init_webdriver()

    def __init_webdriver(self):
        if self.is_main:
            global phantomjs_port
            if phantomjs_port == 0:
                phantomjs_port = get_free_port()
                self.wd_port = phantomjs_port
                wp = Popen([self.__path + "data/" + self.__phantomjs_name,
                            "--webdriver=" + str(self.wd_port)], stdout=PIPE, stderr=PIPE)
                wp.stdout.readline()
                self.__wd_pid = wp.pid
            else:
                self.wd_port = phantomjs_port
            ll = cdll.LoadLibrary
            self.libsr = ll(self.__path + "data/" + self.__lib_name)
            self.libsr.go.restype = ctypes.c_char_p

    def push_watcher(self, name: str, data: dict):
        main_conn.send({
            'action': 'create',
            'object': str(id(self)),
            'watcher_name': name,
            'watcher_data': data
        })

    def __del__(self):
        main_conn.send({
            'action': 'clear',
            'object': str(id(self))
        })

    def watcher(self, name: str, is_run: bool = False) -> Watcher:
        """
        创建一个待启动的监视者，可以根据指定条件作出相应反应。\n
        :param name: 标识名称，不可重复
        :param is_run: 是否在创建时启动，默认为不启动
        :return: 返回一个实例化的Watcher对象
        """
        w = Watcher(name, is_run, self)
        return w

    def start_watcher(self, name: str) -> None:
        """
        启动一个已有的监视者。\n
        :param name: 监视者标识名称
        :return: 无
        """
        main_conn.send({
            'action': 'start',
            'object': str(id(self)),
            'watcher_name': name
        })

    def pause_watcher(self, name: str) -> None:
        """
        暂停一个已有的监视者。\n
        :param name: 监视者标识名称
        :return: 无
        """
        main_conn.send({
            'action': 'pause',
            'object': str(id(self)),
            'watcher_name': name
        })

    def delete_watcher(self, name: str) -> None:
        """
        删除一个已有的监视者。\n
        :param name: 监视者标识名称
        :return: 无
        """
        main_conn.send({
            'action': 'delete',
            'object': str(id(self)),
            'watcher_name': name
        })

    def __logger(self):
        syslog_save_path = ""
        syslog_file = None
        messages = self.device.con.sse("SysLogger")
        for msg in messages:
            log_str = str(msg.data)
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

    def set_syslog_save_start(self, save_path: str = sys.path[0] + "/syslog/", save_name: str = None,
                              save_keyword: str = "") -> None:
        """
        设置保存设备log开始。\n
        :param save_path: 保存文件路径，指定一个文件夹的相对或绝对路径，默认在当前脚本目录下的syslog文件夹
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
        设置存放xpath信息的ini文件路径(默认为当前脚本目录下的xpath_list.ini)。\n
        :param path: 文件路径
        :return: 无
        """
        self.__xpath_file = path

    def set_screenshots_path(self, path: str) -> None:
        """
        设置存放系统截图的文件夹路径(默认为当前脚本目录下的screenshots文件夹)。\n
        :param path: 文件夹路径
        :return: 无
        """
        self.__screenshots = path

    def screenshot(self, path: str = None) -> str:
        """
        获取设备当前屏幕截图。\n
        :param path: 截图存放路径(默认为前脚本目录下的screenshots文件夹或者用户通过Device.set_screenshots_path(path: str)接口设置的路径)
        :return: 截图名称
        """
        if path is None:
            path = self.__screenshots
        if not os.path.exists(path):
            os.makedirs(path)
        img_base64 = str(self.con.get(path="getScreenShot").read(), 'utf-8').split(',')[0]
        current_remote_time = self.con.get(path="getSystemTime").read()
        file_name = str(current_remote_time, 'utf-8') + ".png"
        image = open(path + "/" + file_name, "wb")
        image.write(base64.b64decode(img_base64))
        image.close()
        return file_name

    def get_framework_info(self) -> dict:
        """
        获取设备内的测试框架信息。\n
        :return: 字典形式信息键值对，可能为空
        """
        json_str = str(self.con.get(path="getFrameworkInfo").read(), 'utf-8')
        if json_str == "":
            return {}
        return json.loads(json_str)

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
        conf.read(self.__xpath_file, encoding='utf-8')
        return conf.get(sop_id, key)

    def has_environment(self, key: str, module: str = "General") -> bool:
        """
        获取指定环境变量是否存在。\n
        :param key: 键
        :param module: 模块名称，默认值：General
        :return:
        """
        if not os.path.exists(self.__environment_file):
            f = open(self.__environment_file, "w")
            f.close()
        conf = configparser.ConfigParser()
        conf.read(self.__environment_file)
        if not conf.has_section(module):
            return False
        return conf.has_option(module, key)

    def get_environment(self, key: str, module: str = "General") -> str:
        """
        获取支撑脚本执行的环境变量，保存在脚本目录下的environment.ini文件中。\n
        :param key: 键
        :param module: 模块名称，默认值：General
        :return: 环境变量值
        """
        if not os.path.exists(self.__environment_file):
            f = open(self.__environment_file, "w")
            f.close()
        conf = configparser.ConfigParser()
        conf.read(self.__environment_file)
        return conf.get(module, key)

    def refresh_layout(self) -> None:
        """
        刷新当前设备的UI布局信息。\n
        :return: 无
        """
        if self.is_main:
            self.xml_string = str(self.con.get(path="getLayoutXML").read(), 'utf-8').replace('\x08', '')
            self.__xml_time = time.time()
            watcher_xml_queue.put({'xml': self.xml_string, 'time': self.__xml_time})
        else:
            data = {'xml': '', 'time': 0}
            while not self.__xml_queue.empty():
                data = self.__xml_queue.get()
            if data['time'] > self.__xml_time:
                self.xml_string = data['xml']
                self.__xml_time = data['time']
            else:
                self.xml_string = str(self.con.get(path="getLayoutXML").read(), 'utf-8').replace('\x08', '')
                self.__xml_time = time.time()

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

    def get_topmost_info(self) -> dict:
        """
        获取当前显示顶层的应用信息。\n
        :return: 字典格式的应用信息
        """
        info = {'sopid': '', 'uiappid': '', 'syberdroid': False}
        for i in range(0, 10):
            try:
                self.refresh_layout()
                selector = etree.XML(self.xml_string.encode('utf-8'))
                info['sopid'] = selector.get("sopId")
                info['uiappid'] = selector.get("uiAppId")
                info['syberdroid'] = selector.get("androidApp") == "1"
                break
            except etree.XMLSyntaxError:
                continue
        return info

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

    def get_text_item_list_full_screen(self, rotation: int = None) -> List[TextItemFromOcr]:
        """
        全屏截图进行OCR图像识别获取文本元素实例化对象列表。\n
        :param rotation: 元素的旋转角度，默认自动获取
        :return: TextItemFromOcr对象列表
        """
        pr = rotation
        if pr is None:
            screen_orientation = self.get_screen_orientation()
            if screen_orientation == ScreenOrientation.PRIMARY or screen_orientation == ScreenOrientation.PORTRAIT:
                pr = 0
            elif screen_orientation == ScreenOrientation.LANDSCAPE:
                pr = 90
            elif screen_orientation == ScreenOrientation.INVERTED_PORTRAIT:
                pr = 180
            else:
                pr = 270
        image_base64 = self.grab_image_to_base64(int(self.__width / 2), int(self.__height / 2), self.__width, self.__height)
        im = Image.open(io.BytesIO(base64.b64decode(image_base64)))
        rotate_im = im.rotate(pr, expand=True)
        width, height = rotate_im.size
        buffered = io.BytesIO()
        rotate_im.save(buffered, format="PNG")
        base64_rotated_image = base64.b64encode(buffered.getvalue()).decode()
        if self.__ocr_server:
            res = requests.post(url=self.__ocr_server,
                                data=bytes("@$START$@" + base64_rotated_image + "@$END$@", 'utf-8'))
            text_item_info_list = json.loads(res.content)
        else:
            image = open(sys.path[0] + "/orc_temp_image.png", "wb")
            imdata = base64.b64decode(base64_rotated_image)
            image.write(imdata)
            image.close()
            reader = easyocr.Reader(['ch_sim', 'en'], gpu=True, model_storage_directory=self.__ocr_mods)
            text_item_info_list = reader.readtext(sys.path[0] + '/orc_temp_image.png')
        text_item_list = []
        for text_item_info in text_item_info_list:
            x = text_item_info[0][0][0]
            y = text_item_info[0][0][1]
            w = text_item_info[0][2][0] - x
            h = text_item_info[0][2][1] - y
            text = text_item_info[1]
            vector_x = x - width / 2
            vector_y = y - height / 2
            rotate_vector_x, rotate_vector_y = rotate_point_clockwise((vector_x, vector_y), (0, 0), pr)
            real_x = int(self.__width / 2) + rotate_vector_x
            real_t = int(self.__height / 2) + rotate_vector_y
            text_item_list.append(TextItemFromOcr(real_x, real_t, w, h, pr, text, self))
        return text_item_list

    def get_text_item_list(self, item: Item, rotation: int = None) -> List[TextItemFromOcr]:
        """
        根据元素控件的截图进行OCR图像识别获取文本元素实例化对象列表。\n
        :param item: 传入的元素控件
        :param rotation: 元素的旋转角度，默认自动获取
        :return: TextItemFromOcr对象列表
        """
        pr = rotation
        if pr is None:
            pr = item.rotation()
        image_base64 = item.grab_image_to_base64()
        im = Image.open(io.BytesIO(base64.b64decode(image_base64)))
        rotate_im = im.rotate(pr, expand=True)
        width, height = rotate_im.size
        buffered = io.BytesIO()
        rotate_im.save(buffered, format="PNG")
        base64_rotated_image = base64.b64encode(buffered.getvalue()).decode()
        if self.__ocr_server:
            res = requests.post(url=self.__ocr_server, data=bytes("@$START$@" + base64_rotated_image + "@$END$@", 'utf-8'))
            text_item_info_list = json.loads(res.content)
        else:
            image = open(sys.path[0] + "/orc_temp_image.png", "wb")
            imdata = base64.b64decode(base64_rotated_image)
            image.write(imdata)
            image.close()
            reader = easyocr.Reader(['ch_sim', 'en'], gpu=True, model_storage_directory=self.__ocr_mods)
            text_item_info_list = reader.readtext(sys.path[0] + '/orc_temp_image.png')
        text_item_list = []
        for text_item_info in text_item_info_list:
            x = text_item_info[0][0][0]
            y = text_item_info[0][0][1]
            w = text_item_info[0][2][0] - x
            h = text_item_info[0][2][1] - y
            text = text_item_info[1]
            vector_x = x - width / 2
            vector_y = y - height / 2
            rotate_vector_x, rotate_vector_y = rotate_point_clockwise((vector_x, vector_y), (0, 0), pr)
            real_x = item.center_x_to_global() + rotate_vector_x
            real_t = item.center_y_to_global() + rotate_vector_y
            text_item_list.append(TextItemFromOcr(real_x, real_t, w, h, pr, text, self))
        return text_item_list

    def support_rotate_screen(self) -> bool:
        """
        读取配置文件获取设备是否支持旋转屏幕。\n
        :return: 支持返回True，否则为False
        """
        if self.has_environment("ROTATE_SCREEN"):
            if not bool(int(self.get_environment("ROTATE_SCREEN"))):
                return False
        return True

    def get_support_device_number_for_sms_send(self) -> str:
        """
        获取可发送短信的辅助机电话号码。\n
        :return: 电话号码字符串，如果无可用电话号码则返回空字符串
        """
        if self.__support_device_server:
            headers = {'Accept': 'text/plain; charset=UTF-8'}
            request = urllib.request.Request(url=self.__support_device_server + "/getSendSmsNumber",
                                             headers=headers, method="GET")
            reply = urllib.request.urlopen(request, timeout=self.default_timeout)
            return reply.read().decode('utf-8')
        return ''

    def get_support_device_number_for_sms_recv(self) -> str:
        """
        获取可接收短信的辅助机电话号码。\n
        :return: 电话号码字符串，如果无可用电话号码则返回空字符串
        """
        if self.__support_device_server:
            headers = {'Accept': 'text/plain; charset=UTF-8'}
            request = urllib.request.Request(url=self.__support_device_server + "/getRecvSmsNumber",
                                             headers=headers, method="GET")
            reply = urllib.request.urlopen(request, timeout=self.default_timeout)
            return reply.read().decode('utf-8')
        return ''

    def send_sms_with_support_device(self, support_number: str, message: str, self_number: str) -> bool:
        """
        通过辅助机向本机发送短信。注意：每台辅助机在发送短信后有10秒冷却时间。\n
        :param support_number: 获取到的辅助机号码
        :param message: 短信内容
        :param self_number: 本机号码
        :return: 成功返回True，否则返回False
        """
        if self.__support_device_server:
            headers = {'Accept': 'text/plain; charset=UTF-8'}
            request = urllib.request.Request(url=self.__support_device_server + "/sendSms?support=" + support_number
                                                 + "&message=" + quote_plus(message) + "&test=" + self_number,
                                             headers=headers, method="GET")
            reply = urllib.request.urlopen(request, timeout=self.default_timeout)
            return reply.read().decode('utf-8') == "true"
        return False

    def get_latest_sms_from_support_device_inbox(self, support_number: str, self_number: str) -> str:
        """
        获取辅助机短信收件箱中最新一条本机发送的短信内容。\n
        :param support_number: 获取到的辅助机号码
        :param self_number: 本机号码
        :return: 短信内容或空字符串
        """
        if self.__support_device_server:
            headers = {'Accept': 'text/plain; charset=UTF-8'}
            request = urllib.request.Request(url=self.__support_device_server + "/recvSms?support=" + support_number
                                                 + "&test=" + self_number,
                                             headers=headers, method="GET")
            reply = urllib.request.urlopen(request, timeout=self.default_timeout)
            return reply.read().decode('utf-8')
        return ''

    def get_support_device_number_for_voice(self) -> (str, str):
        """
        获取可接打电话的辅助机电话号码。\n
        :return: 电话号码字符串和token，如果无可用电话号码则返回两个空字符串，调用辅助机语音电话相关接口时需要携带token验证，token会在无操作30秒钟后失效
        """
        if self.__support_device_server:
            headers = {'Accept': 'text/plain; charset=UTF-8'}
            request = urllib.request.Request(url=self.__support_device_server + "/getPhoneNumber",
                                             headers=headers, method="GET")
            reply = urllib.request.urlopen(request, timeout=self.default_timeout)
            reply_str = reply.read().decode('utf-8')
            if ',' in reply_str:
                return reply_str.split(',')[0], reply_str.split(',')[1]
        return '', ''

    def call_voice_with_support_device(self, token: str, self_number: str, timeout: int = 60) -> bool:
        """
        通过辅助机拨打语音电话。\n
        :param token: 获取到的辅助机验证token
        :param self_number: 本机号码
        :param timeout: 超时时间，默认60秒，超时后辅助机会自动结束通话
        :return: 成功返回True，否则返回False
        """
        if self.__support_device_server:
            headers = {'Accept': 'text/plain; charset=UTF-8'}
            request = urllib.request.Request(url=self.__support_device_server + "/call?token=" + token
                                                 + "&test=" + self_number + "&timeout=" + str(timeout),
                                             headers=headers, method="GET")
            reply = urllib.request.urlopen(request, timeout=self.default_timeout)
            return reply.read().decode('utf-8') == 'true'
        return False

    def answer_voice_with_support_device(self, token: str, self_number: str, timeout: int = 60) -> bool:
        """
        辅助机等待来电并接听。注意：需要在调用此接口后并且在超时时间内向辅助机拨打电话\n
        :param token: 获取到的辅助机验证token
        :param self_number: 本机号码
        :param timeout: 超时时间，默认60秒，超时后辅助机会自动结束等待或结束通话
        :return: 成功返回True，否则返回False
        """
        if self.__support_device_server:
            headers = {'Accept': 'text/plain; charset=UTF-8'}
            request = urllib.request.Request(url=self.__support_device_server + "/answer?token=" + token
                                                 + "&test=" + self_number + "&timeout=" + str(timeout),
                                             headers=headers, method="GET")
            reply = urllib.request.urlopen(request, timeout=self.default_timeout)
            return reply.read().decode('utf-8') == 'true'
        return False

    def end_call_with_support_device(self, token: str) -> bool:
        """
        立即结束辅助机正在进行的语音电话。\n
        :param token: 获取到的辅助机验证token
        :return: 成功返回True，否则返回False
        """
        if self.__support_device_server:
            headers = {'Accept': 'text/plain; charset=UTF-8'}
            request = urllib.request.Request(url=self.__support_device_server + "/endCall?token=" + token,
                                             headers=headers, method="GET")
            reply = urllib.request.urlopen(request, timeout=self.default_timeout)
            return reply.read().decode('utf-8') == 'true'
        return False

    def reject_voice_with_support_device(self, token: str, self_number: str, wait_time: int = 0, timeout: int = 60) -> bool:
        """
        辅助机等待来电并拒接。注意：需要在调用此接口后并且在超时时间内向辅助机拨打电话\n
        :param token: 获取到的辅助机验证token
        :param self_number: 本机号码
        :param wait_time: 振铃等待时间，默认0秒
        :param timeout: 超时时间，默认60秒，超时后辅助机会自动结束等待
        :return: 成功返回True，否则返回False
        """
        if self.__support_device_server:
            headers = {'Accept': 'text/plain; charset=UTF-8'}
            request = urllib.request.Request(url=self.__support_device_server + "/waitEndCall?token=" + token
                                                 + "&test=" + self_number + "&wait_time=" + str(wait_time)
                                                 + "&timeout=" + str(timeout),
                                             headers=headers, method="GET")
            reply = urllib.request.urlopen(request, timeout=self.default_timeout)
            return reply.read().decode('utf-8') == 'true'
        return False
