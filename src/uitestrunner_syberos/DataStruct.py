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

import enum


class FileInfo:
    """
    文件/文件夹信息。\n
    :ivar name: 名称
    :ivar type: 类型
    :ivar size: 大小(byte)
    :ivar suffix: 后缀(最后一个"."符号之后的字符串，如果没有则为空字符串)
    :ivar permission: 权限的数字表示
    :ivar last_modified: 最后修改时间(秒)
    :ivar last_read: 最后读取时间(秒)
    :ivar owner: 拥有者名称
    :ivar owner_id: 拥有者ID
    :ivar group: 用户组名称
    :ivar group_id: 用户组ID
    """
    class Type(enum.Enum):
        """
        文件类型。\n
        :ivar FILE: 文件(包括有效的符号连接)
        :ivar DIRECTORY: 文件夹
        :ivar OTHER: 其他类型
        """
        OTHER = -1
        FILE = 0
        DIRECTORY = 1
    name = str()
    type = Type
    size = int()
    suffix = str()
    permission = int()
    last_modified = int()
    last_read = int()
    owner = str()
    owner_id = int()
    group = str()
    group_id = int()


class Point:
    """
    坐标点。\n
    :param x: 横向坐标点
    :param y: 纵向坐标点
    :ivar x: 横向坐标点
    :ivar y: 纵向坐标点
    """
    x = int()
    y = int()

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y


class LockState(enum.Enum):
    """
    锁屏状态。\n
    :ivar LOCKED: 已锁定
    :ivar UNLOCKED: 已解锁
    """
    LOCKED = 0
    UNLOCKED = 1


class DisplayState(enum.Enum):
    """
    显示器状态。\n
    :ivar ON: 亮屏
    :ivar OFF: 灭屏
    :ivar DIM: 暗屏
    """
    ON = 0
    OFF = 1
    DIM = 2


class ScreenOrientation(enum.Enum):
    """
    屏幕方向。\n
    :ivar PRIMARY: 主要方向 一般为0度
    :ivar PORTRAIT: 纵向 一般为0度
    :ivar LANDSCAPE: 横向 一般为90度
    :ivar INVERTED_PORTRAIT: 反纵向 一般为180度
    :ivar INVERTED_LANDSCAPE: 反横向 一般为270度
    """
    PRIMARY = 0
    PORTRAIT = 1
    LANDSCAPE = 2
    INVERTED_PORTRAIT = 3
    INVERTED_LANDSCAPE = 4


class Controller(enum.Enum):
    """
    控制端类型。\n
    :ivar ANYWHERE: 非兼容平台
    :ivar WINDOWS_AMD64: x86_64架构的windows平台，推荐windows10
    :ivar LINUX_X86_64: x86_64架构的linux平台，推荐ubuntu18.04
    :ivar DARWIN_X86_64: x86_64架构的macOSX平台，推荐Catalina
    """
    ANYWHERE = 0
    WINDOWS_AMD64 = 1
    LINUX_X86_64 = 2
    DARWIN_X86_64 = 3


class WatcherActive(enum.Enum):
    """
    Watcher执行动作类型。\n
    :ivar CLICK: 点击屏幕
    :ivar LAUNCH: 启动应用
    :ivar PAUSE: 按键
    :ivar STOP: 停止应用
    """
    CLICK = 0
    LAUNCH = 1
    PAUSE = 2
    STOP = 3


class Keys(enum.Enum):
    """
    设备按键。\n
    :ivar BACK: 返回按键
    :ivar HOME: 主页按键
    """
    BACK = 0
    HOME = 1


class AudioManagerRoleType(enum.Enum):
    """
    音频管理角色类型。\n
    :ivar AM_ROLE_INVALID: 无效的
    :ivar AM_ROLE_RINGTONE: 来电铃声
    :ivar AM_ROLE_NOTIFICATION: 通知提示音
    :ivar AM_ROLE_MEDIA: 多媒体
    :ivar AM_ROLE_SYSTEM: 系统提示音
    :ivar AM_ROLE_PHONE: 通话
    :ivar AM_ROLE_ALARM: 闹钟铃声
    :ivar AM_ROLE_KEYTONE: 按键提示音
    :ivar AM_ROLE_MAX: ...
    """
    AM_ROLE_INVALID = 0
    AM_ROLE_RINGTONE = 1
    AM_ROLE_NOTIFICATION = 2
    AM_ROLE_MEDIA = 3
    AM_ROLE_SYSTEM = 4
    AM_ROLE_PHONE = 5
    AM_ROLE_ALARM = 6
    AM_ROLE_KEYTONE = 7
    AM_ROLE_MAX = 8


class AudioManagerPortType(enum.Enum):
    """
    音频端口类型。\n
    :ivar AM_PORT_OUTPUT_IHF: 免提输出
    :ivar AM_PORT_OUTPUT_HEADPHONE: 耳机输出
    :ivar AM_PORT_OUTPUT_HEADSET: 耳麦输出
    :ivar AM_PORT_CALLON_EARPIECE: 通话听筒输出
    :ivar AM_PORT_CALLON_HEADPHONE: 通话耳机输出
    :ivar AM_PORT_CALLON_HEADSET: 通话耳麦输出
    :ivar AM_PORT_CALLON_SPEAKER: 通话扬声器输出
    :ivar AM_PORT_OUTPUT_IHFHEADPHONE: 耳机免提输出
    :ivar AM_PORT_CALLON_BLUETOOTH: 通话蓝牙输出
    :ivar AM_PORT_INPUT_MIC: 主麦克风输入
    :ivar AM_PORT_INPUT_SECOND_MIC: 次麦克风输入
    :ivar AM_PORT_INPUT_HEADSET_MIC: 耳麦输入
    :ivar AM_PORT_OUTPUT_AUX_DIGITAL: 辅助数字输出
    :ivar AM_PORT_INVALID: 无效的
    """
    AM_PORT_OUTPUT_IHF = 0
    AM_PORT_OUTPUT_HEADPHONE = 1
    AM_PORT_OUTPUT_HEADSET = 2
    AM_PORT_CALLON_EARPIECE = 3
    AM_PORT_CALLON_HEADPHONE = 4
    AM_PORT_CALLON_HEADSET = 5
    AM_PORT_CALLON_SPEAKER = 6
    AM_PORT_OUTPUT_IHFHEADPHONE = 7
    AM_PORT_CALLON_BLUETOOTH = 8
    AM_PORT_INPUT_MIC = 9
    AM_PORT_INPUT_SECOND_MIC = 10
    AM_PORT_INPUT_HEADSET_MIC = 11
    AM_PORT_OUTPUT_AUX_DIGITAL = 12
    AM_PORT_INVALID = 13


class Orientation(enum.Enum):
    """
    设备方向。\n
    :ivar UNDEFINED: 未定义
    :ivar TOP_UP: 上边框朝上
    :ivar TOP_DOWN: 上边框朝下
    :ivar LEFT_UP: 左边框朝上
    :ivar RIGHT_UP: 有边框朝上
    :ivar FACE_UP: 正面朝上
    :ivar FACE_DOWN: 正面朝下
    """
    UNDEFINED = 0
    TOP_UP = 1
    TOP_DOWN = 2
    LEFT_UP = 3
    RIGHT_UP = 4
    FACE_UP = 5
    FACE_DOWN = 6
