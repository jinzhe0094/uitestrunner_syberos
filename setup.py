from setuptools import setup, find_packages
setup(
    name='uitestrunner_syberos',
    version='0.32.5',
    author='Jinzhe Wang',
    description='A ui automated testing tool for SyberOS',
    author_email='wangjinzhe@syberos.com',
    url='http://www.syberos.cn/',
    project_urls={
        "API": "https://jinzhe0094.github.io/uitestrunner-syberos-api-doc/"
    },
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=["uitestrunner_syberos.Device",
                "uitestrunner_syberos.Item",
                "uitestrunner_syberos.Connection",
                "uitestrunner_syberos.Events",
                "uitestrunner_syberos.Watcher",
                "uitestrunner_syberos.setup",
                "uitestrunner_syberos.__main__",
                "uitestrunner_syberos.selenium_phantomjs",
                "uitestrunner_syberos.DataStruct"],
    package_data={
        "uitestrunner_syberos": ["data/*",
                                 "data/ghostdriver/*",
                                 "data/ghostdriver/request_handlers/*",
                                 "data/ghostdriver/third_party/*",
                                 "data/ghostdriver/third_party/webdriver-atoms/*"]
    },
    install_requires=["sseclient",
                      "paramiko",
                      "scp",
                      "lxml",
                      "urllib3",
                      "opencv-python==4.5.3.56",
                      "numpy",
                      "psutil",
                      "sympy",
                      "scikit-build",
                      "Pillow"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6, <4"
)
