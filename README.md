# 元心智能移动操作系统UI自动化测试框架
* 适用与SyberOS5.0及以上版本，包括5.5及以上的安卓兼容版本。
* 推荐适用环境：python3.8+ubuntu1804/MacOS。python3版本过高或过低可能存在依赖安装失败的问题。
## 安装
1.更新pip工具至最新版本：
```commandline
python3.8 -m pip install --upgrade pip
```
2.安装uitestrunner-syberos：
```commandline
python3.8 -m pip install uitestrunner-syberos
```
> 如果在中国大陆下载太慢的话可以换源，在命令后面添加参数`-i https://mirrors.aliyun.com/pypi/simple/`
## 快速开始
1.准备设备。确保设备已经连接至电脑，并开启USB调试模式。通过ssh或adb/cdb等方式登录设备。执行命令以开启UI自动化测试服务guiautotestd：
```commandline
guiautotest-ctl enable
reboot
```
> * ssh用户名密码默认为`developer`，密码为`system`。
> * 每台设备只需要执行一次即可。执行后设备会自动重启。

2.连接及测试。SyberOS设备的USB端口一般默认为rndis模式，设备地址为`192.168.100.100`，guiautotestd服务端口为`10008`。通过浏览器访问`http://192.168.100.100:10008`，即可打开UIMonitor界面如下图：
![图片访问失败](https://github.com/jinzhe0094/uitestrunner_syberos/blob/890e740c4b1d0894f40d14f59e9e6b348cfebaec/docs/image/uimonitor.png?raw=true)
> * UIMonitor工具用于以可视化的方式查看设备上的UI元素的布局信息，以及各个元素的详细属性信息和定位信息等。同时也支持一定的远程控制功能，如屏幕的点击、滑动等操作。
> * 部分SyberOS的设备可能根据项目要求的不同而使用了其它USB端口模式，如adb、cdb等。如果是此种情况应通过adb/cdb工具的端口转发功能将guiautotestd的服务端口映射到本地。命令示例如下：
>   ```commandline
>   adb forward tcp:10008 tcp:10008
>   ```
>   此时则改由通过`http://127.0.0.1:10008`访问UIMonitor。
 
