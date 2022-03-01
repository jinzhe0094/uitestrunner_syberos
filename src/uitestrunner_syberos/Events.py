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
import urllib.parse
from time import sleep
from lxml import etree
import time
import json
from typing import List
from urllib3 import encode_multipart_formdata
from .DataStruct import *


class Events:
    """
    模拟事件类。
    """
    device = None

    def __init__(self, d):
        self.device = d

    @staticmethod
    def __reply_status_check(reply):
        if reply.status == 200:
            return True
        return False

    def get_blank_timeout(self) -> int:
        """
        获取设备由暗屏状态至灭屏状态的超时时间。\n
        :return: 时间(单位:秒)
        """
        return int(self.device.con.get(path="getBlankTimeout").read())

    def set_blank_timeout(self, timeout: int) -> bool:
        """
        设置设备由暗屏状态至灭屏状态的超时时间。\n
        :param timeout: 时间(单位:秒)
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(self.device.con.get(path="setBlankTimeout", args="sec=" + str(timeout)))

    def get_dim_timeout(self) -> int:
        """
        获取设备由亮屏状态至暗屏状态的超时时间。\n
        :return: 时间(单位:秒)
        """
        return int(self.device.con.get(path="getDimTimeout").read())

    def set_dim_timeout(self, timeout: int) -> bool:
        """
        设置设备由亮屏状态至暗屏状态的超时时间。\n
        :param timeout: 时间(单位:秒)
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(self.device.con.get(path="setDimTimeout", args="sec=" + str(timeout)))

    def set_display_on(self) -> bool:
        """
        设置设备屏幕状态为亮屏。\n
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(self.device.con.get(path="setDisplayState", args="state=0"))

    def set_display_off(self) -> bool:
        """
        设置设备屏幕状态为灭屏。\n
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(self.device.con.get(path="setDisplayState", args="state=1"))

    def set_display_dim(self) -> bool:
        """
        设置设备屏幕状态为暗屏。\n
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(self.device.con.get(path="setDisplayState", args="state=0")) and \
            self.__reply_status_check(self.device.con.get(path="setDisplayState", args="state=2"))

    def get_display_state(self) -> DisplayState:
        """
        获取设备当前的屏幕状态。\n
        :return: DisplayState枚举值
        """
        reply = int(str(self.device.con.get(path="getDisplayState").read(), 'utf-8'))
        return DisplayState(reply)

    def lock(self) -> bool:
        """
        将设备锁屏设置为锁定状态。\n
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(self.device.con.get(path="setLockState", args="state=0"))

    def unlock(self) -> bool:
        """
        将设备锁屏设置为解锁状态。\n
        :return: 成功返回True，否则为False
        """
        dis_state = int(str(self.device.con.get(path="getDisplayState").read(), 'utf-8'))
        if dis_state == 0 or dis_state == 2:
            return self.__reply_status_check(self.device.con.get(path="setLockState", args="state=1"))
        elif dis_state == 1:
            if self.set_display_on():
                sleep(1)
                return self.__reply_status_check(self.device.con.get(path="setLockState", args="state=1"))
        return False

    def get_lock_state(self) -> LockState:
        """
        获取设备锁屏当前的锁定状态。\n
        :return: LockState枚举值
        """
        reply = int(str(self.device.con.get(path="getLockState").read(), 'utf-8'))
        return LockState(reply)

    def submit_string(self, text: str) -> bool:
        """
        向当前拥有焦点的元素控件提交文本(模拟输入法事件)。\n
        :param text: 文本字符串
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(
            self.device.con.get(path="sendCommitString", args="str=" + urllib.parse.quote(text)))

    def click(self, point: Point, delay: int = 0) -> bool:
        """
        点击屏幕。\n
        :param point: 坐标点类Point对象
        :param delay: 点击延时时间(单位:毫秒)，默认无延时
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(self.device.con.get(path="sendTouchEvent", args="points=" + str(point.x)
                                                                                         + "|" + str(point.y)
                                                                                         + "&delay=" + str(delay)))

    def multi_click(self, points: List[Point], delay: int = 0) -> bool:
        """
        多指点击屏幕。\n
        :param points: 坐标点类Point对象列表
        :param delay: 点击延时时间(单位:毫秒)，默认无延时
        :return: 成功返回True，否则为False
        """
        args = ""
        for point in points:
            args += str(point.x) + "|" + str(point.y)
            if points.index(point) != len(points) - 1:
                args += ","
        return self.__reply_status_check(self.device.con.get(path="sendTouchEvent", args="points=" + args
                                                                                         + "&delay=" + str(delay)))

    def swipe(self, p1: Point, p2: Point) -> bool:
        """
        滑动屏幕。\n
        :param p1: 坐标点类Point对象，起始点
        :param p2: 坐标点类Point对象，终点
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(self.device.con.get(path="sendSlideEvent", args="sliders=" + str(p1.x)
                                                                                         + "|" + str(p1.y)
                                                                                         + "->" + str(p2.x)
                                                                                         + "|" + str(p2.y)))

    def multi_swipe(self, points1: List[Point], points2: List[Point]) -> bool:
        """
        多指滑动屏幕。\n
        :param points1: 坐标点类Point对象列表，起始点
        :param points2: 坐标点类Point对象列表，终点
        :return: 成功返回True，否则为False
        """
        args = ""
        for point1 in points1:
            args += str(point1.x) + "|" + str(point1.y) \
                    + "->" + str(points2[points1.index(point1)].x) \
                    + "|" + str(points2[points1.index(point1)].y)
            if points1.index(point1) != len(points1) - 1:
                args += ","
        return self.__reply_status_check(self.device.con.get(path="sendSlideEvent", args="sliders=" + args))

    def power(self, delay: int = 0) -> bool:
        """
        点击设备电源按键。\n
        :param delay: 点击延时时间(单位:毫秒)，默认无延时
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(self.device.con.get(path="sendPowerKeyEvent", args="delay=" + str(delay)))

    def back(self, delay: int = 0) -> bool:
        """
        点击设备返回按键。\n
        :param delay: 点击延时时间(单位:毫秒)，默认无延时
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(self.device.con.get(path="sendBackKeyEvent", args="delay=" + str(delay)))

    def home(self, delay: int = 0, timeout: int = None) -> bool:
        """
        点击设备主屏幕按键。\n
        :param delay: 点击延时时间(单位:毫秒)，默认无延时
        :param timeout: 超时时间(单位:秒)，默认为框架超时时间
        :return: 成功返回True，否则为False
        """
        if delay > 0:
            return self.__reply_status_check(self.device.con.get(path="sendHomeKeyEvent", args="delay=" + str(delay)))
        if not timeout:
            timeout = self.device.default_timeout
        die_time = int(time.time()) + timeout
        while int(time.time()) < die_time:
            if self.__reply_status_check(self.device.con.get(path="sendHomeKeyEvent")):
                self.device.refresh_layout()
                selector = etree.XML(self.device.xml_string.encode('utf-8'))
                if selector.get("sopId") == "home-screen(FAKE_VALUE)":
                    return True
                else:
                    self.device.con.get(path="sendHomeKeyEvent")
            sleep(0.5)
        return False

    def menu(self, delay: int = 0) -> bool:
        """
        点击设备菜单按键。\n
        :param delay: 点击延时时间(单位:毫秒)，默认无延时
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(self.device.con.get(path="sendMenuKeyEvent", args="delay=" + str(delay)))

    def volume_up(self, delay: int = 0) -> bool:
        """
        点击设备音量上按键。\n
        :param delay: 点击延时时间(单位:毫秒)，默认无延时
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(self.device.con.get(path="sendVolumeUpKeyEvent", args="delay=" + str(delay)))

    def volume_down(self, delay: int = 0) -> bool:
        """
        点击设备音量下按键。\n
        :param delay: 点击延时时间(单位:毫秒)，默认无延时
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(self.device.con.get(path="sendVolumeDownKeyEvent", args="delay=" + str(delay)))

    def set_rotation_allowed(self, allowed: bool = True) -> bool:
        """
        设置设备自动旋转屏幕开关状态。\n
        :param allowed: 开关状态，True为开启，False为关闭
        :return: 成功返回True，否则为False
        """
        if allowed:
            return self.__reply_status_check(self.device.con.get(path="setRotationAllowed", args="allowed=1"))
        else:
            return self.__reply_status_check(self.device.con.get(path="setRotationAllowed", args="allowed=0"))

    def get_rotation_allowed(self) -> bool:
        """
        获取设备自动旋转屏幕开关状态。\n
        :return: 开关状态，True为开启，False为关闭
        """
        reply = int(str(self.device.con.get(path="getRotationAllowed").read(), 'utf-8'))
        if reply == 1:
            return True
        return False

    def get_screen_orientation(self) -> ScreenOrientation:
        """
        获取设备屏幕方向。\n
        :return: ScreenOrientation枚举值
        """
        return ScreenOrientation(int(str(self.device.con.get(path="getScreenOrientation").read(), 'utf-8')))

    def upload_file(self, file_path: str, remote_path: str) -> bool:
        """
        上传文件至设备。\n
        :param file_path: 控制端原文件路径
        :param remote_path: 设备中目标路径
        :return: 成功返回True，否则为False
        """
        file_name = file_path.split("/")[len(file_path.split("/")) - 1]
        if file_name == "":
            raise Exception('error: the file path format is incorrect, and the transfer folder is not supported')
        if remote_path.split("/")[len(remote_path.split("/")) - 1] == "":
            remote_path += file_name
        header = {
            "content-type": "application/json",
            "FileName": remote_path
        }
        f = open(file_path, 'rb')
        data = {'file': (file_name, f.read())}
        f.close()
        encode_data = encode_multipart_formdata(data)
        data = encode_data[0]
        header['Content-Type'] = encode_data[1]
        return bool(int(str(self.device.con.post(path="upLoadFile", headers=header, data=data).read(), 'utf-8')))

    def file_exist(self, file_path: str) -> bool:
        """
        判断设备中指定文件是否存在。\n
        :param file_path: 设备中文件路径
        :return: 存在返回True，否则为False
        """
        return bool(int(str(self.device.con.get(path="checkFileExist", args="filename=" + file_path).read(), 'utf-8')))

    def dir_exist(self, dir_path: str) -> bool:
        """
        判断设备中指定文件夹是否存在。\n
        :param dir_path: 设备中文件夹路径
        :return: 存在返回True，否则为False
        """
        return self.file_exist(dir_path)

    def file_remove(self, file_path: str) -> bool:
        """
        删除设备中指定文件。\n
        :param file_path: 设备中文件路径
        :return: 成功返回True，否则为False
        """
        return bool(int(str(self.device.con.get(path="fileRemove", args="filename=" + file_path).read(), 'utf-8')))

    def dir_remove(self, dir_path: str) -> bool:
        """
        删除设备中指定文件夹。\n
        :param dir_path: 设备中文件夹路径
        :return: 成功返回True，否则为False
        """
        return bool(int(str(self.device.con.get(path="dirRemove", args="dirname=" + dir_path).read(), 'utf-8')))

    def file_move(self, source_path: str, target_path: str) -> bool:
        """
        移动/重命名设备中指定文件。\n
        :param source_path: 设备中原始文件路径/名称
        :param target_path: 设备中目标文件路径/名称
        :return: 成功返回True，否则为False
        """
        return bool(int(str(
            self.device.con.get(path="fileMove", args="source=" + source_path + "&target=" + target_path).read(),
            'utf-8')))

    def dir_move(self, source_path: str, target_path: str) -> bool:
        """
        移动/重命名设备中指定文件夹。\n
        :param source_path: 设备中原始文件夹路径/名称
        :param target_path: 设备中目标文件夹路径/名称
        :return: 成功返回True，否则为False
        """
        return self.file_move(source_path, target_path)

    def file_copy(self, source_path: str, target_path: str) -> bool:
        """
        复制设备中指定文件。\n
        :param source_path: 设备中原始文件路径
        :param target_path: 设备中目标文件路径
        :return: 成功返回True，否则为False
        """
        return bool(int(str(
            self.device.con.get(path="fileCopy", args="source=" + source_path + "&target=" + target_path).read(),
            'utf-8')))

    def dir_copy(self, source_path: str, target_path: str) -> bool:
        """
        复制设备中指定文件夹。\n
        :param source_path: 设备中原始文件夹路径
        :param target_path: 设备中目标文件夹路径
        :return: 成功返回True，否则为False
        """
        return bool(
            int(str(self.device.con.get(path="dirCopy", args="source=" + source_path + "&target=" + target_path).read(),
                    'utf-8')))

    def dir_list(self, dir_path: str) -> List[FileInfo]:
        """
        获取设备中指定文件夹内的目录信息。\n
        :param dir_path: 设备中指定路径
        :return: FileInfo列表
        """
        json_str = str(self.device.con.get(path="dirList", args="dirname=" + dir_path).read(), 'utf-8')
        json_obj = json.loads(json_str)
        result = []
        for info in json_obj['list']:
            temp = FileInfo()
            temp.name = info['name']
            temp.size = info['size']
            temp.permission = info['permission']
            temp.type = FileInfo.Type(info['type'])
            temp.suffix = info['suffix']
            temp.last_read = info['lastRead']
            temp.last_modified = info['lastModified']
            temp.owner = info['owner']
            temp.owner_id = info['ownerid']
            temp.group = info['group']
            temp.group_id = info['groupid']
            result.append(temp)
        return result

    def mkdir(self, dir_path: str) -> bool:
        """
        在设备中创建一个文件夹。\n
        :param dir_path: 设备中要创建的文件夹路径
        :return: 成功返回True，否则为False
        """
        return bool(int(str(self.device.con.get(path="mkdir", args="dirname=" + dir_path).read(), 'utf-8')))

    def is_installed(self, sopid: str) -> bool:
        """
        判断指定应用是否已安装。\n
        :param sopid: 指定应用的sopid
        :return: 已安装返回True，否则为False
        """
        return bool(int(str(self.device.con.get(path="isAppInstalled", args="sopid=" + sopid).read(), 'utf-8')))

    def is_uninstallable(self, sopid: str) -> bool:
        """
        判断指定应用是否允许卸载。\n
        :param sopid: 指定应用的sopid
        :return: 允许卸载返回True，否则为False
        """
        return bool(int(str(self.device.con.get(path="isAppUninstallable", args="sopid=" + sopid).read(), 'utf-8')))

    def install(self, file_path: str) -> bool:
        """
        安装应用。\n
        :param file_path: 控制端.sop文件的路径
        :return: 成功返回True，否则为False
        """
        if self.upload_file(file_path, "/tmp/"):
            file_name = file_path.split("/")[len(file_path.split("/")) - 1]
            self.device.con.get(path="install", args="filepath=/tmp/" + file_name)
            return True
        return False

    def uninstall(self, sopid: str) -> bool:
        """
        卸载应用。\n
        :param sopid: 要卸载的应用sopid
        :return: 成功返回True，否则为False
        """
        return bool(int(str(self.device.con.get(path="uninstall", args="sopid=" + sopid).read(), 'utf-8')))

    def system_time(self) -> int:
        """
        获取设备系统时间。\n
        :return: unix时间戳(自1970年1月1日0点0分0秒至今的总秒数)
        """
        return int(str(self.device.con.get(path="getDatetime").read(), 'utf-8'))

    def set_system_time(self, secs: int) -> bool:
        """
        设置设备系统时间。\n
        :param secs: unix时间戳(自1970年1月1日0点0分0秒至今的总秒数)
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(self.device.con.get(path="setDatetime", args="datetime=" + str(secs)))

    def get_system_auto_time(self) -> bool:
        """
        获取设备自动获取时间功能的开关状态。\n
        :return: 开启返回True，否则为False
        """
        return bool(int(str(self.device.con.get(path="getAutoDatetime").read(), 'utf-8')))

    def set_system_auto_time(self, state: bool) -> bool:
        """
        设置设备自动获取时间功能的开关状态。\n
        :param state: 开关状态，开启为True，关闭为False
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(self.device.con.get(path="setAutoDatetime", args="state=" + str(int(state))))

    def latest_toast(self) -> str:
        """
        获取系统最新一次弹出的toast文本(设备会自动清除已被读取或覆盖的toast信息)\n
        :return: 文本字符串
        """
        return str(self.device.con.get(path="getLatestToast").read(), 'utf-8')

    def clear_app_data(self, sopid: str) -> bool:
        """
        清除应用数据。\n
        :param sopid: 应用sopid
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(self.device.con.get(path="clearAppData", args="sopid=" + sopid))

    def get_panel_state(self) -> bool:
        """
        获取设备快捷面板展开状态。\n
        :return: 展开返回True，否则为False
        """
        return bool(int(str(self.device.con.get(path="getPanelState").read(), 'utf-8')))

    def set_panel_open(self) -> bool:
        """
        设置设备快捷面板为展开状态。\n
        :return: 成功返回True，否则为False
        """
        if not self.get_panel_state():
            return self.__reply_status_check(self.device.con.get(path="setPanelState"))
        return True

    def set_panel_close(self) -> bool:
        """
        设置设备快捷面板为收起状态。\n
        :return: 成功返回True，否则为False
        """
        if self.get_panel_state():
            return self.__reply_status_check(self.device.con.get(path="setPanelState"))
        return True

    def launch(self, sopid: str, uiappid: str, timeout: int = None) -> bool:
        """
        启动应用。\n
        :param sopid: 应用sopid
        :param uiappid: 应用uiappid
        :param timeout: 超时时间(单位:秒)，默认为框架超时时间
        :return: 成功返回True，否则为False
        """
        self.device.refresh_layout()
        self.device.con.get(path="launchApp", args="sopid=" + sopid + "&" + "uiappid=" + uiappid)
        if timeout is None:
            timeout = self.device.default_timeout
        die_time = int(time.time()) + timeout
        while int(time.time()) < die_time:
            self.device.refresh_layout()
            selector = etree.XML(self.device.xml_string.encode('utf-8'))
            if selector.get("sopId") == sopid:
                return True
            self.device.con.get(path="launchApp", args="sopid=" + sopid + "&" + "uiappid=" + uiappid)
            sleep(1)
        return False

    def close(self, sopid: str, uiappid: str) -> bool:
        """
        关闭应用。\n
        :param sopid: 应用sopid
        :param uiappid: 应用uiappid
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(
            self.device.con.get(path="quitApp", args="sopid=" + sopid + "&uiappid=" + uiappid))

    def is_topmost(self, sopid: str) -> bool:
        """
        判断指定应用是否显示在屏幕最上层。\n
        :param sopid: 指定应用的sopid
        :return: 在最上层返回True，否则为False
        """
        self.device.refresh_layout()
        selector = etree.XML(self.device.xml_string.encode('utf-8'))
        if selector.get("sopId") == sopid:
            return True
        return False

    def get_volume(self, role_type: AudioManagerRoleType) -> int:
        """
        获取指定角色的当前音量值。\n
        :param role_type: AudioManagerRoleType枚举值
        :return: 音量值
        """
        return int(self.device.con.get(path="getVolume", args="type=" + str(role_type.value)))

    def set_volume(self, role_type: AudioManagerRoleType, volume: int) -> bool:
        """
        设置指定角色的音量值。\n
        :param role_type: AudioManagerRoleType枚举值
        :param volume: 要设置的音量值
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(
            self.device.con.get(path="setVolume", args="type=" + str(role_type.value) + "&volume=" + str(volume)))

    def get_volume_steps(self) -> int:
        """
        获取音量设置总步数。\n
        :return: 步数
        """
        return int(self.device.con.get(path="getVolumeSteps"))

    def get_volume_by_step(self, role_type: AudioManagerRoleType) -> int:
        """
        获取指定角色的当前音量设置步数。\n
        :param role_type: AudioManagerRoleType枚举值
        :return: 步数
        """
        return int(self.device.con.get(path="getVolumeByStep", args="type=" + str(role_type.value)))

    def set_volume_by_step(self, role_type: AudioManagerRoleType, step: int) -> bool:
        """
        设置指定角色的音量步数。\n
        :param role_type: AudioManagerRoleType枚举值
        :param step: 要设置的音量步数
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(
            self.device.con.get(path="setVolumeByStep", args="type=" + str(role_type.value) + "&step=" + str(step)))

    def get_volume_active_role(self) -> AudioManagerRoleType:
        """
        获取当前活跃的音量角色。\n
        :return: AudioManagerRoleType枚举值
        """
        return AudioManagerRoleType(int(self.device.con.get(path="getVolumeActiveRole")))

    def set_audio_output_port(self, port_type: AudioManagerPortType) -> bool:
        """
        设置音频输出端口。\n
        :param port_type: AudioManagerPortType枚举值
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(
            self.device.con.get(path="setAudioOutputPort", args="type=" + str(port_type.value)))

    def get_audio_output_port(self) -> AudioManagerPortType:
        """
        获取音频输出端口。\n
        :return: AudioManagerPortType枚举值
        """
        return AudioManagerPortType(int(self.device.con.get(path="getAudioOutputPort")))

    def set_audio_input_port(self, port_type: AudioManagerPortType) -> bool:
        """
        设置音频输入端口。\n
        :param port_type: AudioManagerPortType枚举值
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(
            self.device.con.get(path="setAudioInputPort", args="type=" + str(port_type.value)))

    def get_audio_input_port(self) -> AudioManagerPortType:
        """
        获取音频输出入端口。\n
        :return: AudioManagerPortType枚举值
        """
        return AudioManagerPortType(int(self.device.con.get(path="getAudioInputPort")))

    def max_brightness(self) -> int:
        """
        获取系统最大屏幕亮度值。\n
        :return: 亮度值
        """
        return int(self.device.con.get(path="maxBrightness"))

    def get_brightness(self) -> int:
        """
        获取系统当前屏幕亮度值。\n
        :return: 亮度值
        """
        return int(self.device.con.get(path="getBrightness"))

    def set_brightness(self, brightness: int) -> bool:
        """
        设置系统屏幕亮度值。\n
        :param brightness: 亮度值
        :return: 成功返回True，否则为False
        """
        return bool(self.device.con.get(path="setBrightness", args="brightness=" + str(brightness)))

    def set_auto_brightness(self, enable: bool) -> bool:
        """
        设置自动系统屏幕亮度。\n
        :param enable: 开关状态
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(
            self.device.con.get(path="setAutoBrightness", args="enable=" + str(enable)))

    def get_auto_brightness(self) -> bool:
        """
        获取自动系统屏幕亮度状态。\n
        :return: 开关状态
        """
        return bool(self.device.con.get(path="getAutoBrightness"))

    def send_orientation_event(self, orientation: Orientation) -> bool:
        """
        发送设备方向sensor模拟事件(此接口会自动屏蔽物理sensor的数据上报)。\n
        :param orientation: Orientation枚举值
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(
            self.device.con.get(path="sendOrientationEvent", args="orientation=" + str(orientation.value)))

    def recover_orientation_sensor(self):
        """
        恢复设备方向物理sensor的数据上报功能。\n
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(self.device.con.get(path="recoverOrientationSensor"))

    def send_ambient_light_event(self, lux: int) -> bool:
        """
        发送环境光sensor模拟事件(此接口会自动屏蔽物理sensor的数据上报)。\n
        :param lux: 亮度值
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(
            self.device.con.get(path="sendAmbientLightEvent", args="lux=" + str(lux)))

    def recover_ambient_light_sensor(self):
        """
        恢复环境光物理sensor的数据上报功能。\n
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(self.device.con.get(path="recoverAmbientLightSensor"))

    def send_proximity_event(self, within_proximity: bool) -> bool:
        """
        发送接近sensor模拟事件(此接口会自动屏蔽物理sensor的数据上报)。\n
        :param within_proximity: 时候接近
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(
            self.device.con.get(path="sendProximityEvent", args="withinProximity=" + str(int(within_proximity))))

    def recover_proximity_sensor(self):
        """
        恢复接近物理sensor的数据上报功能。\n
        :return: 成功返回True，否则为False
        """
        return self.__reply_status_check(self.device.con.get(path="recoverProximitySensor"))

    def is_network_available(self):
        """
        获取当前网络状态是否可用。\n
        :return: 网络可用状态
        """
        return bool(int(str(self.device.con.get(path="isNetworkAvailable").read(), 'utf-8')))

    def connect_open_wifi(self, ssid: str, timeout: int = None):
        """
        连接设备至开放WiFi网络。\n
        :param ssid: WiFi网络名称
        :param timeout: 超时时间(单位:秒)，默认为框架超时时间
        :return:
        """
        if timeout is None:
            timeout = self.device.default_timeout
        return bool(int(str(self.device.con.get(path="connectOpenWiFi", args="ssid=" + ssid
                                                                             + "&timeout="
                                                                             + str(timeout)).read(), 'utf-8')))
