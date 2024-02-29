# Copyright (C) <2021-2022>  YUANXIN INFORMATION TECHNOLOGY GROUP CO.LTD and Jinzhe Wang
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
from .DataStruct import *
from time import sleep
import math


def rotate_point_clockwise(point, center, angle):
    # 计算向量AB
    vector_ab = [point[0] - center[0], center[1] - point[1]]

    # 将角度转换为弧度
    angle_radians = math.radians(angle)

    # 计算旋转后的向量坐标
    x_prime = vector_ab[0] * math.cos(-angle_radians) - vector_ab[1] * math.sin(-angle_radians)
    y_prime = vector_ab[0] * math.sin(-angle_radians) + vector_ab[1] * math.cos(-angle_radians)

    # 计算旋转后的点B的坐标
    b_x = center[0] + x_prime
    b_y = center[1] - y_prime

    return b_x, b_y


class TextItemFromOcr:
    """
    ocr识别到的文本元素类型。
    """

    def __init__(self, x: int, y: int, w: int, h: int, r: int, text: str, d=None):
        self.device = d
        self.__x = x
        self.__y = y
        self.__w = w
        self.__h = h
        self.__r = r
        self.__cx, self.__cy = rotate_point_clockwise((x + int(w / 2), y + int(h / 2)),
                                                      (x, y), r)
        self.__text = text

    def x(self) -> int:
        """
        获取元素的左上角相对于全局的映射横坐标整数值。\n
        :return: 横坐标整数值
        """
        return int(self.__x)

    def y(self) -> int:
        """
        获取元素的左上角相对于全局的映射纵坐标整数值。\n
        :return: 纵坐标整数值
        """
        return int(self.__y)

    def width(self) -> int:
        """
        获取元素控件的宽度整数值。\n
        :return: 宽度整数值
        """
        return int(self.__w)

    def height(self) -> int:
        """
        获取元素控件的高度整数值。\n
        :return: 高度整数值
        """
        return int(self.__h)

    def center_x(self) -> int:
        """
        获取元素的中心点相对于全局的映射横坐标整数值。\n
        :return: 横坐标整数值
        """
        return int(self.__cx)

    def center_y(self) -> int:
        """
        获取元素的中心点相对于全局的映射纵坐标整数值。\n
        :return: 纵坐标整数值
        """
        return int(self.__cy)

    def text(self) -> str:
        """
        获取元素的文本信息。\n
        :return: 文本字符串
        """
        return self.__text

    def click(self, delay: int = 0) -> bool:
        """
        点击文本。\n
        :param delay: 点击延时时间(单位:毫秒)，默认无延时
        :return: 成功返回True，否则为False
        """
        return self.device.click(Point(int(self.__cx), int(self.__cy)), delay)

    def submit_string(self, text: str) -> bool:
        """
        向元素控件提交文本(模拟输入法事件)。\n
        :param text: 要提交的文本字符串
        :return: 成功返回True，否则为False
        """
        self.click()
        sleep(2)
        return self.device.submit_string(text)
