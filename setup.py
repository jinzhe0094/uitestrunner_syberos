from setuptools import setup, find_packages


setup(
    name='uitestrunner_syberos',
    version='2.6.2',
    author='Jinzhe Wang',
    description='A ui automated testing tool for SyberOS',
    long_description=open('README.md', 'r').read(),
    long_description_content_type='text/markdown',
    author_email='wangjinzhe@syberos.com',
    url='http://www.syberos.cn/',
    project_urls={
        "Source": "https://github.com/jinzhe0094/uitestrunner_syberos",
        "Api Doc": "https://doc.jinzhe.wang/uts/"
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
                      "urllib3<=1.26.18",
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
