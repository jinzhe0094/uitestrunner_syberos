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

from .Device import Device
from .Connection import Connection
from .Events import Events
from .Item import Item
from .Watcher import *
from .DataStruct import *
from .selenium_phantomjs import *
from .TextItemFromOcr import TextItemFromOcr
import os
import shutil
from pathlib import Path
import ocrCraftModel4uts
import ocrLangModel4uts


ocr_mods_path = os.path.dirname(os.path.abspath(__file__)) + "/ocr_models/"
if not Path(ocr_mods_path).exists():
    os.mkdir(ocr_mods_path)
else:
    if not Path(ocr_mods_path).is_dir():
        os.remove(os.path.dirname(os.path.abspath(__file__)) + "/ocr_models")
        os.mkdir(ocr_mods_path)
for mod in os.listdir(ocrCraftModel4uts.get_path()):
    if not Path(ocrCraftModel4uts.get_path() + mod).is_dir():
        if not Path(ocr_mods_path + mod).exists():
            shutil.copy(ocrCraftModel4uts.get_path() + mod, ocr_mods_path)
for mod in os.listdir(ocrLangModel4uts.get_path()):
    if not Path(ocrLangModel4uts.get_path() + mod).is_dir():
        if not Path(ocr_mods_path + mod).exists():
            shutil.copy(ocrLangModel4uts.get_path() + mod, ocr_mods_path)
