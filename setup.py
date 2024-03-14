import setuptools
from setuptools import setup, find_packages
import os
import shutil
from pathlib import Path
import ocrCraftModel4uts
import ocrLangModel4uts


ocr_mods_path = os.path.dirname(os.path.abspath(__file__)) + "/uitestrunner_syberos/ocr_models/"
if not Path(ocr_mods_path).exists():
    os.mkdir(ocr_mods_path)
else:
    if not Path(ocr_mods_path).is_dir():
        os.remove(os.path.dirname(os.path.abspath(__file__)) + "/uitestrunner_syberos/ocr_models")
        os.mkdir(ocr_mods_path)
for mod in os.listdir(ocrCraftModel4uts.get_path()):
    if not Path(ocrCraftModel4uts.get_path() + mod).is_dir():
        if not Path(ocr_mods_path + mod).exists():
            shutil.copy(ocrCraftModel4uts.get_path() + mod, ocr_mods_path)
for mod in os.listdir(ocrLangModel4uts.get_path()):
    if not Path(ocrLangModel4uts.get_path() + mod).is_dir():
        if not Path(ocr_mods_path + mod).exists():
            shutil.copy(ocrLangModel4uts.get_path() + mod, ocr_mods_path)


setup(
    name='uitestrunner_syberos',
    version='2.1.5',
    author='Jinzhe Wang',
    description='A ui automated testing tool for SyberOS',
    long_description=open('README.md', 'r').read(),
    long_description_content_type='text/markdown',
    author_email='wangjinzhe@syberos.com',
    url='http://www.syberos.cn/',
    project_urls={
        "Source": "https://github.com/jinzhe0094/uitestrunner_syberos",
        "Api Doc": "https://jinzhe0094.github.io/uitestrunner-syberos-api-doc/"
    },
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=["uitestrunner_syberos.Device",
                "uitestrunner_syberos.Item",
                "uitestrunner_syberos.Connection",
                "uitestrunner_syberos.Events",
                "uitestrunner_syberos.Watcher",
                "uitestrunner_syberos.__main__",
                "uitestrunner_syberos.DataStruct",
                "uitestrunner_syberos.TextItemFromOcr"],
    package_data={
        "uitestrunner_syberos": ["data/*",
                                 "data/ghostdriver/*",
                                 "data/ghostdriver/request_handlers/*",
                                 "data/ghostdriver/third_party/*",
                                 "data/ghostdriver/third_party/webdriver-atoms/*"]
    },
    install_requires=["sseclient",
                      "paramiko",
                      "PyNaCl",
                      "scp",
                      "lxml",
                      "urllib3",
                      "opencv-python",
                      "numpy",
                      "psutil",
                      "sympy",
                      "scikit-build",
                      "Pillow",
                      "easyocr",
                      "torch",
                      "torchvision",
                      "ocrLangModel4uts",
                      "ocrCraftModel4uts"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6, <=3.9"
)
