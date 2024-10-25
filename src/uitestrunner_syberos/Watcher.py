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
import time
import psutil
from typing import TypeVar
from .DataStruct import WatcherActive
from .DataStruct import Keys
from .selenium_phantomjs.webdriver.remote import webdriver


WatchContext_T = TypeVar('WatchContext_T', bound='WatchContext')


class WatchWorker:

    def __init__(self, d, conn, main_pid):
        self.device = d
        self.conn = conn
        self.main_pid = main_pid
        self.__watcher_list = []
        self.__watcher_list_raw = {}

    def __get_list(self):
        if self.conn.poll():
            data = dict(self.conn.recv())
            if data['action'] == 'create':
                if data['object'] not in self.__watcher_list_raw.keys():
                    self.__watcher_list_raw[data['object']] = {}
                self.__watcher_list_raw[data['object']][data['watcher_name']] = data['watcher_data']
            elif data['action'] == 'start':
                if data['object'] in self.__watcher_list_raw.keys():
                    if data['watcher_name'] in self.__watcher_list_raw[data['object']].keys():
                        if 'is_run' in self.__watcher_list_raw[data['object']][data['watcher_name']].keys():
                            self.__watcher_list_raw[data['object']][data['watcher_name']]['is_run'] = True
            elif data['action'] == 'pause':
                if data['object'] in self.__watcher_list_raw.keys():
                    if data['watcher_name'] in self.__watcher_list_raw[data['object']].keys():
                        if 'is_run' in self.__watcher_list_raw[data['object']][data['watcher_name']].keys():
                            self.__watcher_list_raw[data['object']][data['watcher_name']]['is_run'] = False
            elif data['action'] == 'delete':
                if data['object'] in self.__watcher_list_raw.keys():
                    if data['watcher_name'] in self.__watcher_list_raw[data['object']].keys():
                        del self.__watcher_list_raw[data['object']][data['watcher_name']]
            elif data['action'] == 'clear':
                if data['object'] in self.__watcher_list_raw.keys():
                    del self.__watcher_list_raw[data['object']]
            elif data['action'] == 'update_wd_port':
                if data['port'] != self.device.wd_port:
                    self.device.wd_port = data['port']
                    self.device.webdriver = webdriver.WebDriver(command_executor='http://127.0.0.1:'
                                                                                 + str(self.device.wd_port) + '/wd/hub')
            self.__watcher_list = []
            for obj in self.__watcher_list_raw.keys():
                for watcher in self.__watcher_list_raw[obj].values():
                    self.__watcher_list.append(watcher)

    def run(self):
        main_process = psutil.Process(self.main_pid)
        while True:
            time.sleep(1)
            try:
                self.__get_list()
                self.device.refresh_layout()
                if len(self.__watcher_list) == 0:
                    continue
                for watcher in self.__watcher_list:
                    if not watcher['is_run']:
                        continue
                    flag = 0
                    for xpath in watcher['xpath_list']:
                        if self.device.find_item_by_xpath(xpath['sop_id'], xpath['xpath']).exist(0):
                            flag += 1
                    if flag == len(watcher['xpath_list']):
                        main_process.suspend()
                        for xpath in watcher['xpath_list']:
                            if xpath['index'] == watcher['index']:
                                if watcher['active'] == WatcherActive.CLICK:
                                    self.device.find_item_by_xpath(xpath['sop_id'], xpath['xpath']).click()
                                elif watcher['active'] == WatcherActive.PAUSE and watcher['active_key'] == Keys.BACK:
                                    self.device.back()
                                elif watcher['active'] == WatcherActive.PAUSE and watcher['active_key'] == Keys.HOME:
                                    self.device.home()
                                elif watcher['active'] == WatcherActive.LAUNCH:
                                    self.device.launch(watcher['active_sop_id'], watcher['active_ui_app_id'])
                                elif watcher['active'] == WatcherActive.STOP:
                                    self.device.close(watcher['active_sop_id'], watcher['active_ui_app_id'])
                        main_process.resume()
            except Exception as e:
                main_process.resume()
                continue


class Watcher:
    """
    监视者类。
    """

    def __init__(self, name: str, is_run: bool, d):
        self.__watcher_data = {'is_run': is_run}
        self.__watcher_name = name
        self.device = d

    def when(self, sop_id: str, xpath_key: str) -> WatchContext_T:
        """
        设置监视者判断条件。\n
        :param sop_id: 设备应用sopid
        :param xpath_key: 用于查询ini文件中xpath值的键
        :return: 返回上下文WatchContext
        """
        if 'xpath_list' not in self.__watcher_data.keys():
            self.__watcher_data['xpath_list'] = []
        index = len(self.__watcher_data['xpath_list'])
        self.__watcher_data['xpath_list'].append({'index': index,
                                                  'xpath': self.device.get_xpath(sop_id, xpath_key),
                                                  'sop_id': sop_id})
        self.__watcher_data['index'] = index
        return WatchContext(self.__watcher_name, self.__watcher_data, self.device)


class WatchContext:
    """
    监视者上下文类。
    """

    def __init__(self, name: str, data: dict, d):
        self.__watcher_data = data
        self.__watcher_name = name
        self.device = d

    def when(self, sop_id: str, xpath_key: str) -> WatchContext_T:
        """
        设置监视者判断条件。\n
        :param sop_id: 设备应用sopid
        :param xpath_key: 用于查询ini文件中xpath值的键
        :return: 返回上下文WatchContext
        """
        if 'xpath_list' not in self.__watcher_data.keys():
            self.__watcher_data['xpath_list'] = []
        index = len(self.__watcher_data['xpath_list'])
        self.__watcher_data['xpath_list'].append({'index': index,
                                                  'xpath': self.device.get_xpath(sop_id, xpath_key),
                                                  'sop_id': sop_id})
        self.__watcher_data['index'] = index
        return self

    def click(self) -> None:
        """
        如果所有when()接口设置的判断条件均为真时，执行点击操作，点击目标为最后一个when()设定的判断锚点控件。\n
        :return: 无
        """
        self.__watcher_data['active'] = WatcherActive.CLICK
        self.__push()

    def pause(self, key: Keys) -> None:
        """
        如果所有when()接口设置的判断条件均为真时，执行按键操作。\n
        :param key: WatcherActive.Keys类型的枚举值，目前仅支持BACK和HOME
        :return: 无
        """
        self.__watcher_data['active'] = WatcherActive.PAUSE
        self.__watcher_data['active_key'] = key
        self.__push()

    def launch(self, sop_id: str, ui_app_id: str) -> None:
        """
        如果所有when()接口设置的判断条件均为真时，执行启动APP操作。\n
        :param sop_id: 要启动的设备应用sopid
        :param ui_app_id: 要启动的设备应用uiappid
        :return: 无
        """
        self.__watcher_data['active'] = WatcherActive.LAUNCH
        self.__watcher_data['active_sop_id'] = sop_id
        self.__watcher_data['active_ui_app_id'] = ui_app_id
        self.__push()

    def stop(self, sop_id: str, ui_app_id: str) -> None:
        """
        如果所有when()接口设置的判断条件均为真时，执行停止APP操作。\n
        :param sop_id: 要停止的设备应用sopid
        :param ui_app_id: 要停止的设备应用uiappid
        :return: 无
        """
        self.__watcher_data['active'] = WatcherActive.STOP
        self.__watcher_data['active_sop_id'] = sop_id
        self.__watcher_data['active_ui_app_id'] = ui_app_id
        self.__push()

    def __push(self):
        self.device.push_watcher(self.__watcher_name, self.__watcher_data)
