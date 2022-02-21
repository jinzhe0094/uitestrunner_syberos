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
    """
    CLICK = 0
    LAUNCH = 1
    PAUSE = 2


class Keys(enum.Enum):
    """
    设备按键。\n
    :ivar BACK: 返回按键
    :ivar HOME: 主页按键
    """
    BACK = 0
    HOME = 1


class AudioRole(enum.Enum):
    """
    音频角色。\n
    :ivar INVALID: 无效值
    :ivar RINGTONE: 电话铃声
    :ivar NOTIFICATION: 通知铃声
    :ivar MEDIA: 媒体播放
    :ivar SYSTEM: 系统音效
    :ivar PHONE: 通话声音
    :ivar ALARM: 闹铃
    :ivar KEYTONE: 按键音
    """
    INVALID = 0
    RINGTONE = 1
    NOTIFICATION = 2
    MEDIA = 3
    SYSTEM = 4
    PHONE = 5
    ALARM = 6
    KEYTONE = 7
