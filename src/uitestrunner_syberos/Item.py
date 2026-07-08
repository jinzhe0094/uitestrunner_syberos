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
import urllib3.exceptions
import time
# from ctypes import *
import threading
import sympy as sp
import math
from lxml import etree
import cv2
import xml.dom.minidom
import numpy as np
from time import sleep
from .DataStruct import *
from . import Device
from typing import List, Dict


html_string_1 = "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\"><title>render" \
                "</title></head><body style=\"background:#000;clip:rect(auto,auto,auto,auto);" \
                "\"><div id=\"content\" style=\"width:"
html_string_2 = "px;height:"
html_string_3 = "px;clip:rect(auto,auto,auto,auto);position:absolute;overflow:hidden;\">"
html_string_4 = "</div></body></html>"


def compute_ssim(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    计算结构相似性指数SSIM
    """
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2

    img1 = img1.astype(np.float64)
    img2 = img2.astype(np.float64)

    kernel = cv2.getGaussianKernel(11, 1.5)
    window = np.outer(kernel, kernel.T)

    mu1 = cv2.filter2D(img1, -1, window)
    mu2 = cv2.filter2D(img2, -1, window)

    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2 = mu1 * mu2

    sigma1_sq = cv2.filter2D(img1 ** 2, -1, window) - mu1_sq
    sigma2_sq = cv2.filter2D(img2 ** 2, -1, window) - mu2_sq
    sigma12 = cv2.filter2D(img1 * img2, -1, window) - mu1_mu2

    ssim_map = ((2 * mu1_mu2 + c1) * (2 * sigma12 + c2)) / ((mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2))

    return float(np.mean(ssim_map))


def extract_texture_features(img: np.ndarray) -> np.ndarray:
    """
    提取纹理特征（对颜色反转不敏感）

    Args:
        img: 输入图片
    """
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = np.sqrt(grad_x ** 2 + grad_y ** 2)

    # 归一化
    if magnitude.max() > 0:
        magnitude = (magnitude - magnitude.min()) / (magnitude.max() - magnitude.min()) * 255

    return magnitude.astype(np.uint8)


def calculate_similarity(img1: np.ndarray, img2: np.ndarray, texture_only: bool = False) -> float:
    """
    计算两张图片的相似度
    """
    if texture_only:
        # 仅纹理对比：使用纹理特征
        texture1 = extract_texture_features(img1)
        texture2 = extract_texture_features(img2)
        return compute_ssim(texture1, texture2)
    else:
        # 综合对比
        if len(img1.shape) == 3 and len(img2.shape) == 3:
            # 彩色图片：分别计算每个通道
            channels = []
            for i in range(3):
                ssim_val = compute_ssim(img1[:, :, i], img2[:, :, i])
                channels.append(ssim_val)
            return float(np.mean(channels))
        else:
            # 灰度图
            return compute_ssim(img1, img2)


def resize_preserve_aspect(img: np.ndarray, target_size: int, by_width: bool = True) -> np.ndarray:
    """
    保持宽高比缩放图片
    """
    h, w = img.shape[:2]

    if by_width:
        scale = target_size / w
        new_w = target_size
        new_h = int(h * scale)
    else:
        scale = target_size / h
        new_h = target_size
        new_w = int(w * scale)

    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)


def compare_images(img1: cv2.typing.MatLike, img2: cv2.typing.MatLike, texture_only: bool = False, scale_by_width: bool = True, enable_scaling: bool = True) -> float:
    """
    比较两张图片，返回最大相似度和最佳偏移位置

    Args:
        img1: 图片1
        img2: 图片2
        texture_only: True=仅比较纹理，False=综合比较
        scale_by_width: True=按宽度缩放，False=按高度缩放
        enable_scaling: True=启用缩放，False=不缩放

    Returns:
        相似度
    """
    original_h1, original_w1 = img1.shape[:2]
    original_h2, original_w2 = img2.shape[:2]

    if enable_scaling:
        # 启用缩放：大尺寸向小尺寸靠拢
        if scale_by_width:
            target_width = min(original_w1, original_w2)
            img1 = resize_preserve_aspect(img1, target_width, by_width=True)
            img2 = resize_preserve_aspect(img2, target_width, by_width=True)
        else:
            target_height = min(original_h1, original_h2)
            img1 = resize_preserve_aspect(img1, target_height, by_width=False)
            img2 = resize_preserve_aspect(img2, target_height, by_width=False)

    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]

    # 确定基础图片和滑动图片（较大的图片作为基础）
    if h1 * w1 >= h2 * w2:
        base_img, slide_img = img1, img2
        base_h, base_w = h1, w1
        slide_h, slide_w = h2, w2
    else:
        base_img, slide_img = img2, img1
        base_h, base_w = h2, w2
        slide_h, slide_w = h1, w1

    # 检查是否有重叠区域
    if base_h < slide_h or base_w < slide_w:
        return 0.0

    # 遍历所有可能的重叠位置
    max_similarity = -1

    for y in range(0, base_h - slide_h + 1):
        for x in range(0, base_w - slide_w + 1):
            base_region = base_img[y:y + slide_h, x:x + slide_w]
            similarity = calculate_similarity(base_region, slide_img, texture_only)

            if similarity > max_similarity:
                max_similarity = similarity

    return max_similarity


class _WorkerThread(threading.Thread):

    result = None

    def __init__(self, func, args=()):
        super().__init__(args=args)
        self.func = func
        self.args = args

    def run(self) -> None:
        self.result = self.func(*self.args)

    def get_result(self):
        return self.result


class Item:
    """
    元素控件类，通过Device.find_item_by_xpath_key()与Device.find_item_by_xpath()两个接口结果返回实例化对象，不推荐单独使用。\n
    :ivar sopid: 元素控件所在的应用sopid
    :ivar device: 实例化的Device对象
    :ivar node: 对应的xml节点对象
    :ivar xpath: xpath字符串
    """
    __display_width = 0
    __display_height = 0
    __html_string = ""

    def __init__(self, d: Device, s: str = "", xpath: str = "", node=None):
        self.window_node = self.node
        self.rect = []
        self.__attributes = {}
        self.__absolute_xpath = ""
        self.__index_by_same_tag = 0
        self.sopid = s
        self.device = d
        self.__display_width = self.device.display_width()
        self.__display_height = self.device.display_height()
        self.xpath = xpath
        self.node = node
        self.__refresh_node()

    def __generate_absolute_xpath(self, node):
        if node.getparent() is not None:
            bor_list = list(node.getparent())
            if len(bor_list) > 1:
                count = 0
                index = 0
                for bn in bor_list:
                    if bn.tag == node.tag:
                        count += 1
                        if bn == node:
                            index = count
                if count > 1:
                    self.__index_by_same_tag = index
                    self.__absolute_xpath = "/" + node.tag + "[" + str(index) + "]" + self.__absolute_xpath
                else:
                    self.__absolute_xpath = "/" + node.tag + self.__absolute_xpath
            else:
                self.__absolute_xpath = "/" + node.tag + self.__absolute_xpath
            self.__generate_absolute_xpath(node.getparent())
        else:
            self.__absolute_xpath = "/" + node.tag + self.__absolute_xpath

    def __refresh_node(self):
        self.device.refresh_layout()
        if self.xpath != "":
            self.node = None
            self.window_node = None
            for i in range(0, 10):
                try:
                    selector = etree.XML(self.device.xml_string)
                    nodes = selector.xpath(self.xpath)
                    for node in nodes:
                        window_node = node
                        while window_node.getparent().getparent() is not None:
                            window_node = window_node.getparent()
                        if window_node.get("sopid") == self.sopid or self.sopid == "":
                            self.node = node
                            break
                    break
                except etree.XMLSyntaxError:
                    self.device.refresh_layout()
                    continue
        else:
            self.__generate_absolute_xpath(self.node)
            self.xpath = self.__absolute_xpath
        if self.node is None:
            self.__init_attribute()
            return
        if self.node.getparent() is None:
            self.__init_attribute()
            return
        self.window_node = self.node
        while self.window_node.getparent().getparent() is not None:
            self.window_node = self.window_node.getparent()
        self.__refresh_attribute()

    def __refresh_attribute(self):
        self.__attributes["x"] = int(round(float(self.node.get("x"))))
        self.__attributes["y"] = int(round(float(self.node.get("y"))))
        self.__attributes["center_x_to_item"] = int(round(float(self.node.get("centerXToItem"))))
        self.__attributes["center_y_to_item"] = int(round(float(self.node.get("centerYToItem"))))
        self.__attributes["center_x_to_global"] = int(round(float(self.node.get("centerXToGlobal"))))
        self.__attributes["center_y_to_global"] = int(round(float(self.node.get("centerYToGlobal"))))
        self.__attributes["z"] = int(self.node.get("z"))
        self.__attributes["height"] = int(round(float(self.node.get("height"))))
        self.__attributes["width"] = int(round(float(self.node.get("width"))))
        self.__attributes["temp_id"] = self.node.get("tempID")
        self.__attributes["text"] = self.node.get("text")
        self.__attributes["object_name"] = self.node.get("objectName")
        self.__attributes["class_name"] = self.node.tag
        self.__attributes["opacity"] = float(self.node.get("opacity"))
        self.__attributes["enabled"] = bool(int(self.node.get("enabled")))
        self.__attributes["visible"] = bool(int(self.node.get("visible")))
        self.__attributes["focus"] = bool(int(self.node.get("focus")))
        self.__attributes["scale"] = float(self.node.get("scale"))
        self.__attributes["rotation"] = int(self.node.get("rotation"))
        self.__attributes["clip"] = bool(int(self.node.get("clip")))
        self.__attributes["has_contents"] = bool(int(self.node.get("hasContents")))
        self.__attributes["layer_id"] = self.window_node.get("layerid")
        self.__attributes["window_title"] = self.window_node.get("title")
        self.__attributes["sop_id"] = self.window_node.get("sopid")
        self.__attributes["ui_app_id"] = self.window_node.get("uiappid")

    def __init_attribute(self):
        self.__attributes["text"] = str()
        self.__attributes["temp_id"] = str()
        self.__attributes["x"] = int()
        self.__attributes["y"] = int()
        self.__attributes["z"] = int()
        self.__attributes["center_x_to_item"] = int()
        self.__attributes["center_y_to_item"] = int()
        self.__attributes["center_x_to_global"] = int()
        self.__attributes["center_y_to_global"] = int()
        self.__attributes["height"] = int()
        self.__attributes["width"] = int()
        self.__attributes["class_name"] = str()
        self.__attributes["object_name"] = str()
        self.__attributes["opacity"] = float()
        self.__attributes["focus"] = bool()
        self.__attributes["enabled"] = bool()
        self.__attributes["visible"] = bool()
        self.__attributes["scale"] = float()
        self.__attributes["rotation"] = int()
        self.__attributes["clip"] = bool()
        self.__attributes["has_contents"] = bool()
        self.__attributes["layer_id"] = str()
        self.__attributes["window_title"] = str()
        self.__attributes["sop_id"] = str()
        self.__attributes["ui_app_id"] = str()

    def attributes(self, refresh: bool = False) -> Dict:
        """
        获取当前Item对象的属性字典。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 属性字典
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes

    def parent(self, refresh: bool = False) -> 'Item':
        """
        获取当前Item对象的父对象，如没有则返回None。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 父亲对象或None
        """
        if refresh:
            self.__refresh_node()
        if self.node is None:
            return None
        if self.node.getparent() is None:
            return None
        return Item(self.device, self.sopid, "", self.node.getparent())

    def children(self, filter_condition: dict = None, refresh: bool = False) -> List['Item']:
        """
        获取当前Item对象的子对象列表。\n
        :param filter_condition: 用于筛选子对象的属性条件字典
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 子对象列表
        """
        if refresh:
            self.__refresh_node()
        children = []
        if self.node is None:
            return children
        if filter_condition is not None:
            for key in filter_condition.keys():
                if key not in self.__attributes.keys():
                    return children
            for node in list(self.node):
                i = Item(self.device, self.sopid, "", node)
                flag = 0
                for key in filter_condition.keys():
                    if i.attributes()[key] == filter_condition[key]:
                        flag += 1
                if flag == len(filter_condition):
                    children.append(i)
        else:
            for node in list(self.node):
                children.append(Item(self.device, self.sopid, "", node))
        return children

    def previous(self, refresh: bool = False) -> 'Item':
        """
        获取当前Item对象的前一位兄弟对象，如没有则返回None。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 前一位兄弟对象或None
        """
        if refresh:
            self.__refresh_node()
        if self.node is None:
            return None
        if self.node.getparent() is None:
            return None
        return Item(self.device, self.sopid, "", self.node.getprevious())

    def previous_by_same_tag(self, refresh: bool = False) -> 'Item':
        """
        获取当前Item对象的前一位同类兄弟对象，如没有则返回None。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 前一位同类兄弟对象或None
        """
        if refresh:
            self.__refresh_node()
        if self.node is None:
            return None
        if self.node.getparent() is None:
            return None
        pn = self.node.getprevious()
        while pn is not None:
            if pn.tag == self.node.tag:
                return Item(self.device, self.sopid, "", pn)
            pn = pn.getprevious()
        return None

    def next(self, refresh: bool = False) -> 'Item':
        """
        获取当前Item对象的后一位兄弟对象，如没有则返回None。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 后一位兄弟对象或None
        """
        if refresh:
            self.__refresh_node()
        if self.node is None:
            return None
        if self.node.getparent() is None:
            return None
        return Item(self.device, self.sopid, "", self.node.getnext())

    def next_by_same_tag(self, refresh: bool = False) -> 'Item':
        """
        获取当前Item对象的后一位同类兄弟对象，如没有则返回None。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 后一位同类兄弟对象或None
        """
        if refresh:
            self.__refresh_node()
        if self.node is None:
            return None
        if self.node.getparent() is None:
            return None
        nn = self.node.getnext()
        while nn is not None:
            if nn.tag == self.node.tag:
                return Item(self.device, self.sopid, "", nn)
            nn = nn.getnext()
        return None

    def index(self, refresh: bool = False) -> int:
        """
        获取当前Item对象相对于所有兄弟对象的索引值。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 索引值
        """
        if refresh:
            self.__refresh_node()
        if self.node is None:
            return 0
        if self.node.getparent() is None:
            return 0
        return self.node.getparent().index(self.node)

    def index_by_same_tag(self, refresh: bool = False) -> int:
        """
        获取当前Item对象相对于同类兄弟对象的索引值。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 索引值
        """
        if refresh:
            self.__refresh_node()
        return self.__index_by_same_tag

    def x(self, refresh: bool = False) -> int:
        """
        获取元素控件的左上角横坐标整数值。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 横坐标整数值
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["x"]

    def y(self, refresh: bool = False) -> int:
        """
        获取元素控件的左上角纵坐标整数值。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 纵坐标整数值
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["y"]

    def center_x_to_item(self, refresh: bool = False) -> int:
        """
        获取元素控件的中心点相对于父对象的映射横坐标整数值。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 横坐标整数值
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["center_x_to_item"]

    def center_y_to_item(self, refresh: bool = False) -> int:
        """
        获取元素控件的中心点相对于父对象的映射纵坐标整数值。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 纵坐标整数值
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["center_y_to_item"]

    def center_x_to_global(self, refresh: bool = False) -> int:
        """
        获取元素控件的中心点相对于全局的映射横坐标整数值。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 横坐标整数值
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["center_x_to_global"]

    def center_y_to_global(self, refresh: bool = False) -> int:
        """
        获取元素控件的中心点相对于全局的映射纵坐标整数值。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 纵坐标整数值
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["center_y_to_global"]

    def z(self, refresh: bool = False) -> int:
        """
        获取元素控件的z轴坐标整数值。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: z轴坐标整数值
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["z"]

    def scale(self, refresh: bool = False) -> float:
        """
        获取元素控件的缩放系数。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 缩放系数
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["scale"]

    def rotation(self, refresh: bool = False) -> int:
        """
        获取元素控件的顺时针旋转角度。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 角度值
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["rotation"]

    def clip(self, refresh: bool = False) -> bool:
        """
        获取元素控件是否启用了裁切属性。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: bool值，开启裁切为True，否则为False
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["clip"]

    def height(self, refresh: bool = False) -> int:
        """
        获取元素控件的高度整数值。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 高度整数值
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["height"]

    def width(self, refresh: bool = False) -> int:
        """
        获取元素控件的宽度整数值。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 宽度整数值
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["width"]

    def temp_id(self, refresh: bool = False) -> str:
        """
        获取元素控件的临时标识符。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 标识符字符串
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["temp_id"]

    def text(self, refresh: bool = False) -> str:
        """
        获取元素控件的文本信息。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 文本字符串
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["text"]

    def object_name(self, refresh: bool = False) -> str:
        """
        获取元素控件的对象名称，此属性对应开发过程中的qml的id属性，但实际此属性在全局并非绝对唯一。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 对象名称字符串
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["object_name"]

    def class_name(self, refresh: bool = False) -> str:
        """
        获取元素控件的类名。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 类名字符串
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["class_name"]

    def opacity(self, refresh: bool = False) -> float:
        """
        获取元素控件的透明度(0-1的浮点数)。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 透明度值
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["opacity"]

    def enabled(self, refresh: bool = False) -> bool:
        """
        获取元素控件的enabled属性。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 属性值，True为开启，否则为False
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["enabled"]

    def visible(self, refresh: bool = False) -> bool:
        """
        获取元素控件的可访问属性。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 属性值，True为开启，否则为False
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["visible"]

    def focus(self, refresh: bool = False) -> bool:
        """
        获取元素控件是否拥有焦点。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 属性值，拥有焦点为True，否则为False
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["focus"]

    def has_contents(self, refresh: bool = False) -> bool:
        """
        判断元素控件是否拥有可视内容。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 属性值，拥有可视内容为True，否则为False
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["has_contents"]

    def sop_id(self, refresh: bool = False) -> str:
        """
        获取元素控件所属进程的sopid。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: sopid
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["sop_id"]

    def ui_app_id(self, refresh: bool = False) -> str:
        """
        获取元素控件所属进程的uiappid。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: uiappid
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["ui_app_id"]

    def window_title(self, refresh: bool = False) -> str:
        """
        获取元素控件所属进程的窗口title。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 窗口title
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["window_title"]

    def layer_id(self, refresh: bool = False) -> str:
        """
        获取元素控件所属进程的layerid。\n
        :param refresh: 是否刷新布局信息(默认值False)
        :return: 获取元素控件所属进程的layerid
        """
        if refresh:
            self.__refresh_node()
        return self.__attributes["layer_id"]

    def __xml_to_html(self):
        self.__html_string = ""
        tree = xml.dom.minidom.parseString(self.device.xml_string)
        root = tree.documentElement
        if root.hasChildNodes():
            self.__xml_to_html_traverse(root, 0, 0, 0, True)

    def __xml_to_html_traverse(self, node: xml.dom.minidom.Element, index_z: int, x_offset: int, y_offset: int, root: bool = False):
        for child in node.childNodes:
            height = float(child.getAttribute("height"))
            width = float(child.getAttribute("width"))
            cx = float(child.getAttribute("centerXToItem"))
            cy = float(child.getAttribute("centerYToItem"))
            x = cx - (width / 2) - x_offset
            y = cy - (height / 2) - y_offset
            xo = 0
            yo = 0
            if root:
                xo = float(child.getAttribute("xoffset"))
                yo = float(child.getAttribute("yoffset"))
            if float(child.getAttribute("opacity")) != 0 \
                    and int(child.getAttribute("visible")) == 1 \
                    and child.nodeName != "QQuickShaderEffectSource":
                clip = "clip:rect(auto, auto, auto, auto);" if int(child.getAttribute("clip")) == 1 else ""
                z = index_z + int(child.getAttribute("z"))
                scale = child.getAttribute("scale")
                rotation = int(child.getAttribute("rotation"))
                if int(child.getAttribute("hasContents")) == 0:
                    self.__html_string += "<div style=\"position:absolute;z-index:"+str(z)+";left:"+str(x)+"px;top:"+str(y)+"px;width:"+str(width)+"px;height:"+str(height)+"px;-webkit-transform:scale("+scale+") rotate("+str(rotation)+"deg);"+clip+"\">"
                else:
                    if child.getAttribute("tempID") == self.temp_id():
                        self.__html_string += "<div style=\"position:absolute;z-index:"+str(z)+";left:"+str(x)+"px;top:"+str(y)+"px;width:"+str(width)+"px;height:"+str(height)+"px;-webkit-transform:scale("+scale+") rotate("+str(rotation)+"deg);"+clip+"background:#F00;\">"
                    else:
                        self.__html_string += "<div style=\"position:absolute;z-index:"+str(z)+";left:"+str(x)+"px;top:"+str(y)+"px;width:"+str(width)+"px;height:"+str(height)+"px;-webkit-transform:scale("+scale+") rotate("+str(rotation)+"deg);"+clip+"background:#00F;\">"
                if child.hasChildNodes():
                    self.__xml_to_html_traverse(child, z, xo, yo)
                self.__html_string += "</div>"

    def exist(self, timeout: int = None) -> bool:
        """
        判断元素控件是否显示。\n
        :param timeout: 超时时间(单位:秒)，默认为框架超时时间
        :return: 显示为True，超时未显示为False
        """
        if timeout is None:
            timeout = self.device.default_timeout
        die_time = int(time.time()) + timeout
        while True:
            self.rect = self.__exist()
            if len(self.rect) > 0:
                return True
            sleep(0.5)
            if int(time.time()) > die_time:
                break
        return False

    def __exist(self):
        self.__refresh_node()
        if self.node is not None \
                and self.__attributes["visible"] \
                and self.__attributes["opacity"] > 0 \
                and self.__attributes["scale"] != 0 \
                and self.__attributes["width"] > 0 \
                and self.__attributes["height"] > 0:
            image = []
            if self.device.control_host_type == Controller.ANYWHERE:
                tree = xml.dom.minidom.parseString(self.device.xml_string)
                for node in tree.documentElement.childNodes:
                    for n in node.childNodes:
                        if len(image) == 0:
                            image = self.__xml_tree_traversed(n.childNodes, 1)
                        else:
                            image = self.__img_cover(image, self.__xml_tree_traversed(n.childNodes, 1))
            else:
                # html_string = self.device.libsr.go(c_char_p(bytes(self.device.xml_string, "utf-8")),
                #                                    c_char_p(bytes(self.__attributes["temp_id"], "utf-8")),
                #                                    c_int(self.__display_width),
                #                                    c_int(self.__display_height))
                self.__xml_to_html()
                if self.device.is_main:
                    self.device.conn_phantomjs_before()
                try:
                    self.device.webdriver.get("data:text/html;charset=utf-8," +
                                              html_string_1 + str(self.__display_width) +
                                              html_string_2 + str(self.__display_height) +
                                              html_string_3 + self.__html_string +
                                              html_string_4)
                    image = cv2.imdecode(np.frombuffer(base64.b64decode(self.device.webdriver.get_screenshot_as_base64()),
                                                       np.uint8), cv2.COLOR_RGB2BGR)
                except (cv2.error, urllib3.exceptions.ProtocolError) as e:
                    print(e)
                    if self.device.is_main:
                        self.device.conn_phantomjs_after()
                    return []
                if self.device.is_main:
                    self.device.conn_phantomjs_after()
            # win_name = str(self.device.system_time())
            # cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
            # cv2.imshow(win_name, image)
            # cv2.waitKey(0)
            b, g, r = cv2.split(image)
            if len(np.argwhere(r == 255)) > 0:
                return np.argwhere(r == 255)
        return []

    def __xml_tree_traversed(self, nodes, fs):
        all_images = {}
        th_index = 0
        th_list = {}
        for node in nodes:
            th = _WorkerThread(func=self.__draw_item, args=(node, fs, ))
            th_list[th_index] = th
            th.daemon = True
            th_index += 1
        for i in range(th_index):
            th_list[i].start()
        for i in range(th_index):
            th_list[i].join()
            images = th_list[i].get_result()
            for image_z in images:
                if image_z in all_images.keys():
                    all_images[image_z] = self.__img_cover(all_images[image_z], images[image_z])
                else:
                    all_images[image_z] = images[image_z]
        im_list = list(all_images.keys())
        im_list.sort()
        r_image = np.zeros((self.__display_height, self.__display_width), dtype=np.uint8)
        r_image = cv2.cvtColor(r_image, cv2.COLOR_GRAY2BGR)
        for index in im_list:
            r_image = self.__img_cover(r_image, all_images[index])
        return r_image

    def __draw_item(self, node, fs):
        images = {}
        clip = int(node.getAttribute("clip"))
        scale = abs(float(node.getAttribute("scale")) * fs)
        height = round(float(node.getAttribute("height")) * scale)
        width = round(float(node.getAttribute("width")) * scale)
        rotation = 0 - int(round(float(node.getAttribute("rotation"))))
        has_contents = bool(int(node.getAttribute("hasContents")))
        cx = round(float(node.getAttribute("centerXToGlobal")))
        cy = round(float(node.getAttribute("centerYToGlobal")))
        if height > 10000 or width > 10000:
            x = float(node.getAttribute("x"))
            y = float(node.getAttribute("y"))
            cx, cy, width, height = self.__clip_item(float(cx), float(cy), float(width), float(height), x, y,
                                                     0 - rotation)
        if float(node.getAttribute("opacity")) != 0 \
                and int(node.getAttribute("visible")) == 1 \
                and node.nodeName != "QQuickShaderEffectSource":
            index_z = int(node.getAttribute("z"))
            if height > 0 and width > 0:
                image = np.zeros((height, width), dtype=np.uint8)
            else:
                image = np.zeros((self.__display_height, self.__display_width), dtype=np.uint8)
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            if has_contents or (node.nodeName == "QQuickLoader" and node.getAttribute("z") == "10000" and
                                node.getAttribute("tempID") == "temp7"):
                if node.getAttribute("tempID") == self.__attributes["temp_id"]:
                    cv2.rectangle(image, (0, 0), (width, height), (0, 0, 255), -1)
                else:
                    cv2.rectangle(image, (0, 0), (width, height), (255, 0, 0), -1)
                    # cv2.rectangle(image, (0, 0), (width, height),
                    #              (random.randint(0, 255), 0, random.randint(0, 255)), -1)
            else:
                cv2.rectangle(image, (0, 0), (width, height), (0, 255, 0), -1)
            hypotenuse = int(math.sqrt(height ** 2 + width ** 2))
            M1 = np.float32([[1, 0, (hypotenuse - width) / 2], [0, 1, (hypotenuse - height) / 2]])
            image = cv2.warpAffine(image, M1, (hypotenuse, hypotenuse))
            M2 = cv2.getRotationMatrix2D((hypotenuse / 2, hypotenuse / 2), rotation, 1)
            image = cv2.warpAffine(image, M2, (hypotenuse, hypotenuse))
            M3 = np.float32([[1, 0, cx - (hypotenuse / 2)], [0, 1, cy - (hypotenuse / 2)]])
            image = cv2.warpAffine(image, M3, (self.__display_width, self.__display_height))
            if node.childNodes.length > 0:
                c_images = self.__xml_tree_traversed(node.childNodes, scale)
                image = self.__img_cover(image, c_images, clip)
            if index_z in images.keys():
                images[index_z] = self.__img_cover(images[index_z], image)
            else:
                images[index_z] = image
        return images

    def __clip_item(self, cx, cy, width, height, x, y, rotation):
        if width > 10000:
            r_width = 10000
        else:
            r_width = width
        if height > 10000:
            r_height = 10000
        else:
            r_height = height
        diagonal = math.sqrt(r_height ** 2 + r_width ** 2)
        p1x = x
        p1y = y
        p2x = None
        p2y = None
        p3x = 2 * (cx - x) + x
        p3y = 2 * (cy - y) + y
        p4x = None
        p4y = None
        if rotation % 90 == 0:
            if rotation / 90 % 4 == 0:
                p2x = p3x
                p2y = p1y
                p4x = p1x
                p4y = p3y
            elif rotation / 90 % 4 == 1:
                p2x = p1x
                p2y = p3y
                p4x = p3x
                p4y = p1y
            elif rotation / 90 % 4 == 2:
                p2x = p3x
                p2y = p1y
                p4x = p1x
                p4y = p3y
            elif rotation / 90 % 4 == 3:
                p2x = p1x
                p2y = p3y
                p4x = p3x
                p4y = p1y
        elif 0 < rotation % 360 < 90:
            p2x = p1x + self.__cos(rotation % 90) * width
            p2y = p1y + self.__sin(rotation % 90) * width
            p4x = p1x - self.__cos(90 - (rotation % 90)) * height
            p4y = p1y + self.__sin(90 - (rotation % 90)) * height
        elif 90 < rotation % 360 < 180:
            p2x = p1x - self.__sin(rotation % 90) * width
            p2y = p1y + self.__cos(rotation % 90) * width
            p4x = p1x - self.__sin(90 - (rotation % 90)) * height
            p4y = p1y - self.__cos(90 - (rotation % 90)) * height
        elif 180 < rotation % 360 < 270:
            p2x = p1x - self.__cos(rotation % 90) * width
            p2y = p1y - self.__sin(rotation % 90) * width
            p4x = p1x + self.__cos(90 - (rotation % 90)) * height
            p4y = p1y - self.__sin(90 - (rotation % 90)) * height
        elif 270 < rotation % 360 < 360:
            p2x = p1x + self.__sin(rotation % 90) * width
            p2y = p1y - self.__cos(rotation % 90) * width
            p4x = p1x + self.__sin(90 - (rotation % 90)) * height
            p4y = p1y + self.__cos(90 - (rotation % 90)) * height
        if 0 <= p1x <= self.__display_width and 0 <= p1y <= self.__display_height:
            pwx, pwy, phx, phy = self.__compute_vertex(p1x, p1y, p1x, p1y, p2x, p2y, p4x, p4y, width, height,
                                                       r_width, r_height)
            r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
            r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
            return int(r_cx), int(r_cy), int(r_width), int(r_height)
        elif 0 <= p2x <= self.__display_width and 0 <= p2y <= self.__display_height:
            pwx, pwy, phx, phy = self.__compute_vertex(p2x, p2y, p2x, p2y, p1x, p1y, p3x, p3y, width, height,
                                                       r_width, r_height)
            r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
            r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
            return int(r_cx), int(r_cy), int(r_width), int(r_height)
        elif 0 <= p3x <= self.__display_width and 0 <= p3y <= self.__display_height:
            pwx, pwy, phx, phy = self.__compute_vertex(p3x, p3y, p3x, p3y, p4x, p4y, p2x, p2y, width, height,
                                                       r_width, r_height)
            r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
            r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
            return int(r_cx), int(r_cy), int(r_width), int(r_height)
        elif 0 <= p4x <= self.__display_width and 0 <= p4y <= self.__display_height:
            pwx, pwy, phx, phy = self.__compute_vertex(p4x, p4y, p4x, p4y, p3x, p3y, p1x, p1y, width, height,
                                                       r_width, r_height)
            r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
            r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
            return int(r_cx), int(r_cy), int(r_width), int(r_height)
        flag, ix, iy = self.__segment_intersect_display(p1x, p1y, p2x, p2y)
        if flag:
            if width > 10000:
                if math.sqrt((ix - p1x) ** 2 + (iy - p1y) ** 2) < 5000:
                    pwx, pwy, phx, phy = self.__compute_vertex(p1x, p1y, p1x, p1y, p2x, p2y, p4x, p4y, width, height,
                                                               r_width, r_height)
                    r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
                    r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
                    return int(r_cx), int(r_cy), int(r_width), int(r_height)
                elif width - math.sqrt((ix - p1x) ** 2 + (iy - p1y) ** 2) < 5000:
                    pwx, pwy, phx, phy = self.__compute_vertex(p2x, p2y, p2x, p2y, p1x, p1y, p3x, p3y, width, height,
                                                               r_width, r_height)
                    r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
                    r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
                    return int(r_cx), int(r_cy), int(r_width), int(r_height)
                else:
                    sx = p1x + (p2x - p1x) / width * (math.sqrt((ix - p1x) ** 2 + (iy - p1y) ** 2) - 5000)
                    sy = p1y + (p2y - p1y) / width * (math.sqrt((ix - p1x) ** 2 + (iy - p1y) ** 2) - 5000)
                    pwx, pwy, phx, phy = self.__compute_vertex(sx, sy, p1x, p1y, p2x, p2y, p4x, p4y, width, height,
                                                               r_width, r_height)
                    r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
                    r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
                    return int(r_cx), int(r_cy), int(r_width), int(r_height)
            else:
                pwx, pwy, phx, phy = self.__compute_vertex(p1x, p1y, p1x, p1y, p2x, p2y, p4x, p4y, width, height,
                                                           r_width, r_height)
                r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
                r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
                return int(r_cx), int(r_cy), int(r_width), int(r_height)
        flag, ix, iy = self.__segment_intersect_display(p2x, p2y, p3x, p3y)
        if flag:
            if height > 10000:
                if math.sqrt((ix - p2x) ** 2 + (iy - p2y) ** 2) < 5000:
                    pwx, pwy, phx, phy = self.__compute_vertex(p2x, p2y, p2x, p2y, p1x, p1y, p3x, p3y, width, height,
                                                               r_width, r_height)
                    r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
                    r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
                    return int(r_cx), int(r_cy), int(r_width), int(r_height)
                elif height - math.sqrt((ix - p2x) ** 2 + (iy - p2y) ** 2) < 5000:
                    pwx, pwy, phx, phy = self.__compute_vertex(p3x, p3y, p3x, p3y, p4x, p4y, p2x, p2y, width, height,
                                                               r_width, r_height)
                    r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
                    r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
                    return int(r_cx), int(r_cy), int(r_width), int(r_height)
                else:
                    sx = p2x + (p3x - p2x) / height * (math.sqrt((ix - p2x) ** 2 + (iy - p2y) ** 2) - 5000)
                    sy = p2y + (p3y - p2y) / height * (math.sqrt((ix - p2x) ** 2 + (iy - p2y) ** 2) - 5000)
                    pwx, pwy, phx, phy = self.__compute_vertex(sx, sy, p2x, p2y, p1x, p1y, p3x, p3y, width, height,
                                                               r_width, r_height)
                    r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
                    r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
                    return int(r_cx), int(r_cy), int(r_width), int(r_height)
            else:
                pwx, pwy, phx, phy = self.__compute_vertex(p2x, p2y, p2x, p2y, p1x, p1y, p3x, p3y, width, height,
                                                           r_width, r_height)
                r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
                r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
                return int(r_cx), int(r_cy), int(r_width), int(r_height)
        flag, ix, iy = self.__segment_intersect_display(p3x, p3y, p4x, p4y)
        if flag:
            if width > 10000:
                if math.sqrt((ix - p3x) ** 2 + (iy - p3y) ** 2) < 5000:
                    pwx, pwy, phx, phy = self.__compute_vertex(p3x, p3y, p3x, p3y, p4x, p4y, p2x, p2y, width, height,
                                                               r_width, r_height)
                    r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
                    r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
                    return int(r_cx), int(r_cy), int(r_width), int(r_height)
                elif width - math.sqrt((ix - p3x) ** 2 + (iy - p3y) ** 2) < 5000:
                    pwx, pwy, phx, phy = self.__compute_vertex(p4x, p4y, p4x, p4y, p3x, p3y, p1x, p1y, width, height,
                                                               r_width, r_height)
                    r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
                    r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
                    return int(r_cx), int(r_cy), int(r_width), int(r_height)
                else:
                    sx = p3x + (p4x - p3x) / width * (math.sqrt((ix - p3x) ** 2 + (iy - p3y) ** 2) - 5000)
                    sy = p3y + (p4y - p3y) / width * (math.sqrt((ix - p3x) ** 2 + (iy - p3y) ** 2) - 5000)
                    pwx, pwy, phx, phy = self.__compute_vertex(sx, sy, p3x, p3y, p4x, p4y, p2x, p2y, width, height,
                                                               r_width, r_height)
                    r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
                    r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
                    return int(r_cx), int(r_cy), int(r_width), int(r_height)
            else:
                pwx, pwy, phx, phy = self.__compute_vertex(p3x, p3y, p3x, p3y, p4x, p4y, p2x, p2y, width, height,
                                                           r_width, r_height)
                r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
                r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
                return int(r_cx), int(r_cy), int(r_width), int(r_height)
        flag, ix, iy = self.__segment_intersect_display(p4x, p4y, p1x, p1y)
        if flag:
            if height > 10000:
                if math.sqrt((ix - p4x) ** 2 + (iy - p4y) ** 2) < 5000:
                    pwx, pwy, phx, phy = self.__compute_vertex(p4x, p4y, p4x, p4y, p3x, p3y, p1x, p1y, width, height,
                                                               r_width, r_height)
                    r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
                    r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
                    return int(r_cx), int(r_cy), int(r_width), int(r_height)
                elif height - math.sqrt((ix - p4x) ** 2 + (iy - p4y) ** 2) < 5000:
                    pwx, pwy, phx, phy = self.__compute_vertex(p1x, p1y, p1x, p1y, p2x, p2y, p4x, p4y, width, height,
                                                               r_width, r_height)
                    r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
                    r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
                    return int(r_cx), int(r_cy), int(r_width), int(r_height)
                else:
                    sx = p4x + (p1x - p4x) / height * (math.sqrt((ix - p4x) ** 2 + (iy - p4y) ** 2) - 5000)
                    sy = p4y + (p1y - p4y) / height * (math.sqrt((ix - p4x) ** 2 + (iy - p4y) ** 2) - 5000)
                    pwx, pwy, phx, phy = self.__compute_vertex(sx, sy, p4x, p4y, p3x, p3y, p1x, p1y, width, height,
                                                               r_width, r_height)
                    r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
                    r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
                    return int(r_cx), int(r_cy), int(r_width), int(r_height)
            else:
                pwx, pwy, phx, phy = self.__compute_vertex(p4x, p4y, p4x, p4y, p3x, p3y, p1x, p1y, width, height,
                                                           r_width, r_height)
                r_cx = round(pwx + (phx - pwx) / diagonal * (diagonal / 2))
                r_cy = round(pwy + (phy - pwy) / diagonal * (diagonal / 2))
                return int(r_cx), int(r_cy), int(r_width), int(r_height)
        return 0, 0, 0, 0

    def __segment_intersect_display(self, l1x, l1y, l2x, l2y):
        if l2x > l1x:
            sx = l1x
            ex = l2x
        else:
            sx = l2x
            ex = l1x
        if l2y > l1y:
            sy = l1y
            ey = l2y
        else:
            sy = l2y
            ey = l1y
        if l2y - l1y == 0:
            lxb = 0
        else:
            lxb = (l2x - l1x) / (l2y - l1y)
        if l2x - l1x == 0:
            lyb = 0
        else:
            lyb = (l2y - l1y) / (l2x - l1x)
        if sy <= l1y + (0 - l1x) * lyb <= ey and 0 <= l1y + (0 - l1x) * lyb <= self.__display_height:
            return True, 0, l1y + (0 - l1x) * lyb
        if sy <= l1y + (self.__display_width - l1x) * lyb <= ey and 0 <= l1y + (
                self.__display_width - l1x) * lyb <= self.__display_height:
            return True, self.__display_width, l1y + (self.__display_width - l1x) * lyb
        if sx <= l1x + (0 - l1y) * lxb <= ex and 0 <= l1x + (0 - l1y) * lxb <= self.__display_width:
            return True, l1x + (0 - l1y) * lxb, 0
        if sx <= l1x + (self.__display_height - l1y) * lxb <= ex and 0 <= l1x + (
                self.__display_height - l1y) * lxb <= self.__display_width:
            return True, l1x + (self.__display_height - l1y) * lxb, self.__display_height
        return False, 0, 0

    @staticmethod
    def __compute_vertex(sx, sy, jx, jy, wx, wy, hx, hy, w, h, rw, rh):
        pwx = sx + (wx - jx) / w * rw
        pwy = sy + (wy - jy) / w * rw
        phx = sx + (hx - jx) / h * rh
        phy = sy + (hy - jy) / h * rh
        return pwx, pwy, phx, phy

    @staticmethod
    def __sin(x):
        return sp.sin(x * sp.pi / 180)

    @staticmethod
    def __cos(x):
        return sp.cos(x * sp.pi / 180)

    @staticmethod
    def __img_cover(src1, src2, clip=0):
        rows, cols, channels = src2.shape
        roi2 = src2[0:rows, 0:cols]
        if clip == 1:
            src1_2gray = cv2.cvtColor(src1, cv2.COLOR_BGR2GRAY)
            ret1, mask1 = cv2.threshold(src1_2gray, 1, 255, cv2.THRESH_BINARY_INV)
            image_bg1 = cv2.bitwise_and(roi2, roi2, mask=mask1)
            src2 = cv2.subtract(src2, image_bg1)
        B1, G1, R1 = cv2.split(src1)
        zeros = np.zeros(src1.shape[:2], dtype="uint8")
        src1 = cv2.merge([B1, zeros, R1])
        roi1 = src1[0:rows, 0:cols]
        B2, G2, R2 = cv2.split(src2)
        src2 = cv2.merge([B2, zeros, R2])
        src2_2gray = cv2.cvtColor(src2, cv2.COLOR_BGR2GRAY)
        ret2, mask2 = cv2.threshold(src2_2gray, 1, 255, cv2.THRESH_BINARY)
        image_bg = cv2.bitwise_and(roi1, roi1, mask=mask2)
        image = cv2.subtract(src1, image_bg)
        image = cv2.add(image, src2)
        return image

    def click(self, delay: int = 0) -> bool:
        """
        点击元素控件。\n
        :param delay: 点击延时时间(单位:毫秒), 默认无延时
        :return: 成功返回True，否则为False
        """
        if self.node is not None:
            return self.device.click(Point(self.__attributes["center_x_to_global"], self.__attributes["center_y_to_global"]), delay)
        return False

    def click_exist(self, delay: int = 0, timeout: int = None) -> bool:
        """
        判断元素控件是否显示，显示则执行点击操作。\n
        :param delay: 点击延时时间(单位:毫秒), 默认无延时
        :param timeout: 超时时间(单位:秒)，默认为框架超时时间
        :return: 点击成功返回True，失败或不存在返回False
        """
        if self.exist(timeout):
            return self.device.click(Point(self.rect[0][1]+1, self.rect[0][0]+1), delay)
        return False

    def drag(self, p: Point, delay: int = 1):
        """
        将元素控件拖动到指定点位。\n
        :param p: 坐标点类Point对象，目标点
        :param delay: 起始点长按时间，默认1秒
        :return: 成功返回True，否则为False
        """
        return self.device.drag(Point(self.center_x_to_global(), self.center_y_to_global()), p, delay)

    def submit_string(self, text: str) -> bool:
        """
        向元素控件提交文本(模拟输入法事件)。\n
        :param text: 要提交的文本字符串
        :return: 成功返回True，否则为False
        """
        self.click()
        sleep(1)
        return self.device.submit_string(text)

    def grab_image_to_base64(self) -> str:
        """
        获取元素控件的显示范围截图。\n
        :return: 截图的base64形态
        """
        return self.device.grab_image_to_base64(self.__attributes["center_x_to_global"],
                                                self.__attributes["center_y_to_global"],
                                                self.__attributes["width"], self.__attributes["height"],
                                                self.__attributes["rotation"], self.__attributes["scale"])

    def contrast_picture(self, path: str, scale: bool = False, texture_only: bool = False) -> float:
        """
        使用本地的图片文件与当前元素控件截图进行图片比对。\n
        :param path: 本地的图片路径
        :param scale: 对比之前是否通过缩放来统一二者的长或宽，默认为否
        :param texture_only: 只对比纹理，默认为否
        :return: 对比值，值越小越相似
        """
        self.__refresh_node()
        current_pic_base64 = self.grab_image_to_base64()
        if current_pic_base64 == "" or path == "":
            return 1.0

        img_data1 = base64.b64decode(current_pic_base64)
        np_arr1 = np.frombuffer(img_data1, np.uint8)
        img1 = cv2.imdecode(np_arr1, cv2.IMREAD_COLOR)

        img2 = cv2.imread(path)

        return 1.0 - max(compare_images(img1, img2, texture_only, True, scale), compare_images(img1, img2, texture_only, False, scale))

    def contrast_picture_from_base64(self, pic: str, scale: bool = False, texture_only: bool = False) -> float:
        """
        使用图片的base64字符串与当前元素控件截图进行图片比对。\n
        :param pic: 图片的base64字符串
        :param scale: 对比之前是否通过缩放来统一二者的长或宽，默认为否
        :param texture_only: 只对比纹理，默认为否
        :return: 对比值，值越小越相似
        """
        self.__refresh_node()
        return self.device.contrast_picture_from_base64(pic, self.grab_image_to_base64(), scale)


# class ItemN(Item):
#     """
#     新版元素控件类，继承自Item,通过Device.get_item_by_xpath()接口结果返回实例化对象，不推荐单独使用。\n
#     :ivar sopid: 元素控件所在的应用sopid
#     :ivar device: 实例化的Device对象
#     :ivar node: 对应的xml节点对象
#     :ivar xpath: xpath字符串
#     """
#
#     __html_string = ""
#
#     def __init__(self, d: Device, s: str = "", xpath: str = "", node=None):
#         self.window_node = self.node
#         super().__init__(d, s, xpath, node)
#
#     def __refresh_node(self):
#         self.device.refresh_layout()
#         if self.xpath != "":
#             self.node = None
#             self.window_node = None
#             for i in range(0, 10):
#                 try:
#                     selector = etree.XML(self.device.xml_string.encode('utf-8'))
#                     nodes = selector.xpath(self.xpath)
#                     for node in nodes:
#                         window_node = node
#                         while window_node.getparent().getparent() is not None:
#                             window_node = window_node.getparent()
#                         if window_node.get("sopid") == self.sopid or self.sopid == "":
#                             self.node = node
#                             break
#                     break
#                 except etree.XMLSyntaxError:
#                     self.device.refresh_layout()
#                     continue
#         else:
#             self.__generate_absolute_xpath(self.node)
#             self.xpath = self.__absolute_xpath
#         if self.node is None:
#             self.__init_attribute()
#             return
#         if self.node.getparent() is None:
#             self.__init_attribute()
#             return
#         self.window_node = self.node
#         while self.window_node.getparent().getparent() is not None:
#             self.window_node = self.window_node.getparent()
#         self.__refresh_attribute()
#
#     def __init_attribute(self):
#         self.__attributes["text"] = str()
#         self.__attributes["temp_id"] = str()
#         self.__attributes["x"] = int()
#         self.__attributes["y"] = int()
#         self.__attributes["z"] = int()
#         self.__attributes["center_x_to_item"] = int()
#         self.__attributes["center_y_to_item"] = int()
#         self.__attributes["center_x_to_global"] = int()
#         self.__attributes["center_y_to_global"] = int()
#         self.__attributes["height"] = int()
#         self.__attributes["width"] = int()
#         self.__attributes["class_name"] = str()
#         self.__attributes["object_name"] = str()
#         self.__attributes["opacity"] = float()
#         self.__attributes["focus"] = bool()
#         self.__attributes["enabled"] = bool()
#         self.__attributes["visible"] = bool()
#         self.__attributes["scale"] = float()
#         self.__attributes["rotation"] = int()
#         self.__attributes["clip"] = bool()
#         self.__attributes["has_contents"] = bool()
#         self.__attributes["layer_id"] = str()
#         self.__attributes["window_title"] = str()
#         self.__attributes["sop_id"] = str()
#         self.__attributes["ui_app_id"] = str()
#
#     def __refresh_attribute(self):
#         self.__attributes["x"] = int(round(float(self.node.get("x"))))
#         self.__attributes["y"] = int(round(float(self.node.get("y"))))
#         self.__attributes["center_x_to_item"] = int(round(float(self.node.get("a"))))
#         self.__attributes["center_y_to_item"] = int(round(float(self.node.get("b"))))
#         self.__attributes["center_x_to_global"] = int(round(float(self.node.get("d"))))
#         self.__attributes["center_y_to_global"] = int(round(float(self.node.get("g"))))
#         self.__attributes["z"] = int(self.node.get("z"))
#         self.__attributes["height"] = int(round(float(self.node.get("h"))))
#         self.__attributes["width"] = int(round(float(self.node.get("w"))))
#         self.__attributes["temp_id"] = self.node.get("k")
#         self.__attributes["text"] = self.node.get("t")
#         self.__attributes["object_name"] = self.node.get("i")
#         self.__attributes["class_name"] = self.node.tag
#         self.__attributes["opacity"] = float(self.node.get("o"))
#         self.__attributes["enabled"] = bool(int(self.node.get("e")))
#         self.__attributes["visible"] = bool(int(self.node.get("v")))
#         self.__attributes["focus"] = bool(int(self.node.get("f")))
#         self.__attributes["scale"] = float(self.node.get("s"))
#         self.__attributes["rotation"] = int(self.node.get("r"))
#         self.__attributes["clip"] = bool(int(self.node.get("c")))
#         self.__attributes["has_contents"] = bool(int(self.node.get("j")))
#         self.__attributes["layer_id"] = self.window_node.get("layerid")
#         self.__attributes["window_title"] = self.window_node.get("title")
#         self.__attributes["sop_id"] = self.window_node.get("sopid")
#         self.__attributes["ui_app_id"] = self.window_node.get("uiappid")
#
#     def __xml_to_html(self):
#         self.__html_string = ""
#         tree = xml.dom.minidom.parseString(self.device.xml_string)
#         root = tree.documentElement
#         if root.hasChildNodes():
#             self.__xml_to_html_traverse(root, 0, 0, 0, True)
#
#     def __xml_to_html_traverse(self, node: xml.dom.minidom.Element, index_z: int, x_offset: int, y_offset: int, root: bool = False):
#         for child in node.childNodes:
#             height = float(child.getAttribute("h"))
#             width = float(child.getAttribute("w"))
#             cx = float(child.getAttribute("a"))
#             cy = float(child.getAttribute("b"))
#             x = cx - (width / 2) - x_offset
#             y = cy - (height / 2) - y_offset
#             xo = 0
#             yo = 0
#             if root:
#                 xo = float(child.getAttribute("xoffset"))
#                 yo = float(child.getAttribute("yoffset"))
#             if float(child.getAttribute("o")) != 0 \
#                     and int(child.getAttribute("v")) == 1 \
#                     and child.nodeName != "QQuickShaderEffectSource":
#                 clip = "clip:rect(auto, auto, auto, auto);" if int(child.getAttribute("c")) == 1 else ""
#                 z = index_z + int(child.getAttribute("z"))
#                 scale = child.getAttribute("s")
#                 rotation = int(child.getAttribute("r"))
#                 if int(child.getAttribute("j")) == 0:
#                     self.__html_string += "<div style=\"position:absolute;z-index:"+str(z)+";left:"+str(x)+"px;top:"+str(y)+"px;width:"+str(width)+"px;height:"+str(height)+"px;-webkit-transform:scale("+scale+") rotate("+str(rotation)+"deg);"+clip+"\">"
#                 else:
#                     if child.getAttribute("k") == self.temp_id():
#                         self.__html_string += "<div style=\"position:absolute;z-index:"+str(z)+";left:"+str(x)+"px;top:"+str(y)+"px;width:"+str(width)+"px;height:"+str(height)+"px;-webkit-transform:scale("+scale+") rotate("+str(rotation)+"deg);"+clip+"background:#F00;\">"
#                     else:
#                         self.__html_string += "<div style=\"position:absolute;z-index:"+str(z)+";left:"+str(x)+"px;top:"+str(y)+"px;width:"+str(width)+"px;height:"+str(height)+"px;-webkit-transform:scale("+scale+") rotate("+str(rotation)+"deg);"+clip+"background:#00F;\">"
#                 if child.hasChildNodes():
#                     self.__xml_to_html_traverse(child, z, xo, yo)
#                 self.__html_string += "</div>"
#
#     def __exist(self):
#         self.__refresh_node()
#         if self.node is not None \
#                 and self.__attributes["visible"] \
#                 and self.__attributes["opacity"] > 0 \
#                 and self.__attributes["scale"] != 0 \
#                 and self.__attributes["width"] > 0 \
#                 and self.__attributes["height"] > 0:
#             image = []
#             if self.device.control_host_type == Controller.ANYWHERE:
#                 tree = xml.dom.minidom.parseString(self.device.xml_string)
#                 for node in tree.documentElement.childNodes:
#                     for n in node.childNodes:
#                         if len(image) == 0:
#                             image = self.__xml_tree_traversed(n.childNodes, 1)
#                         else:
#                             image = self.__img_cover(image, self.__xml_tree_traversed(n.childNodes, 1))
#             else:
#                 self.__xml_to_html()
#                 if self.device.is_main:
#                     self.device.conn_phantomjs_before()
#                 try:
#                     self.device.webdriver.get("data:text/html;charset=utf-8," +
#                                               html_string_1 + str(self.__display_width) +
#                                               html_string_2 + str(self.__display_height) +
#                                               html_string_3 + self.__html_string +
#                                               html_string_4)
#                     image = cv2.imdecode(np.frombuffer(base64.b64decode(self.device.webdriver.get_screenshot_as_base64()),
#                                                        np.uint8), cv2.COLOR_RGB2BGR)
#                 except (cv2.error, urllib3.exceptions.ProtocolError) as e:
#                     print(e)
#                     if self.device.is_main:
#                         self.device.conn_phantomjs_after()
#                     return []
#                 if self.device.is_main:
#                     self.device.conn_phantomjs_after()
#             b, g, r = cv2.split(image)
#             if len(np.argwhere(r == 255)) > 0:
#                 return np.argwhere(r == 255)
#         return []
#
#     def parent(self, refresh: bool = False) -> 'ItemN':
#         """
#         获取当前ItemN对象的父对象，如没有则返回None。\n
#         :param refresh: 是否刷新布局信息(默认值False)
#         :return: 父亲对象或None
#         """
#         if refresh:
#             self.__refresh_node()
#         if self.node is None:
#             return None
#         if self.node.getparent() is None:
#             return None
#         return ItemN(self.device, "", self.node.getparent())
#
#     def children(self, filter_condition: dict = None, refresh: bool = False) -> List['ItemN']:
#         """
#         获取当前ItemN对象的子对象列表。\n
#         :param filter_condition: 用于筛选子对象的属性条件字典
#         :param refresh: 是否刷新布局信息(默认值False)
#         :return: 子对象列表
#         """
#         if refresh:
#             self.__refresh_node()
#         children = []
#         if self.node is None:
#             return children
#         if filter_condition is not None:
#             for key in filter_condition.keys():
#                 if key not in self.__attributes.keys():
#                     return children
#             for node in list(self.node):
#                 i = ItemN(self.device, "", node)
#                 flag = 0
#                 for key in filter_condition.keys():
#                     if i.attributes()[key] == filter_condition[key]:
#                         flag += 1
#                 if flag == len(filter_condition):
#                     children.append(i)
#         else:
#             for node in list(self.node):
#                 children.append(Item(self.device, self.sopid, "", node))
#         return children
#
#     def previous(self, refresh: bool = False) -> 'ItemN':
#         """
#         获取当前ItemN对象的前一位兄弟对象，如没有则返回None。\n
#         :param refresh: 是否刷新布局信息(默认值False)
#         :return: 前一位兄弟对象或None
#         """
#         if refresh:
#             self.__refresh_node()
#         if self.node is None:
#             return None
#         if self.node.getparent() is None:
#             return None
#         return ItemN(self.device, "", self.node.getprevious())
#
#     def previous_by_same_tag(self, refresh: bool = False) -> 'ItemN':
#         """
#         获取当前ItemN对象的前一位同类兄弟对象，如没有则返回None。\n
#         :param refresh: 是否刷新布局信息(默认值False)
#         :return: 前一位同类兄弟对象或None
#         """
#         if refresh:
#             self.__refresh_node()
#         if self.node is None:
#             return None
#         if self.node.getparent() is None:
#             return None
#         pn = self.node.getprevious()
#         while pn is not None:
#             if pn.tag == self.node.tag:
#                 return ItemN(self.device, "", pn)
#             pn = pn.getprevious()
#         return None
#
#     def next(self, refresh: bool = False) -> 'ItemN':
#         """
#         获取当前ItemN对象的后一位兄弟对象，如没有则返回None。\n
#         :param refresh: 是否刷新布局信息(默认值False)
#         :return: 后一位兄弟对象或None
#         """
#         if refresh:
#             self.__refresh_node()
#         if self.node is None:
#             return None
#         if self.node.getparent() is None:
#             return None
#         return ItemN(self.device, "", self.node.getnext())
#
#     def next_by_same_tag(self, refresh: bool = False) -> 'ItemN':
#         """
#         获取当前ItemN对象的后一位同类兄弟对象，如没有则返回None。\n
#         :param refresh: 是否刷新布局信息(默认值False)
#         :return: 后一位同类兄弟对象或None
#         """
#         if refresh:
#             self.__refresh_node()
#         if self.node is None:
#             return None
#         if self.node.getparent() is None:
#             return None
#         nn = self.node.getnext()
#         while nn is not None:
#             if nn.tag == self.node.tag:
#                 return ItemN(self.device, "", nn)
#             nn = nn.getnext()
#         return None
#
#     def sop_id(self, refresh: bool = False) -> str:
#         """
#         获取元素控件所属进程的sopid。\n
#         :param refresh: 是否刷新布局信息(默认值False)
#         :return: sopid
#         """
#         if refresh:
#             self.__refresh_node()
#         return self.__attributes["sop_id"]
#
#     def ui_app_id(self, refresh: bool = False) -> str:
#         """
#         获取元素控件所属进程的uiappid。\n
#         :param refresh: 是否刷新布局信息(默认值False)
#         :return: uiappid
#         """
#         if refresh:
#             self.__refresh_node()
#         return self.__attributes["ui_app_id"]
#
#     def window_title(self, refresh: bool = False) -> str:
#         """
#         获取元素控件所属进程的窗口title。\n
#         :param refresh: 是否刷新布局信息(默认值False)
#         :return: 窗口title
#         """
#         if refresh:
#             self.__refresh_node()
#         return self.__attributes["window_title"]
#
#     def layer_id(self, refresh: bool = False) -> str:
#         """
#         获取元素控件所属进程的layerid。\n
#         :param refresh: 是否刷新布局信息(默认值False)
#         :return: 获取元素控件所属进程的layerid
#         """
#         if refresh:
#             self.__refresh_node()
#         return self.__attributes["layer_id"]
