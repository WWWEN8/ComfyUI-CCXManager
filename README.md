CCXManage是专门为SD-PPP插件开发的一个辅助插件。

之前用过SD-PPP节点的小伙伴都感觉非常麻烦，SD-PPP节点升级了，另外Photoshop还要比较复杂去手动去安装插件，造成SD-PPP不能及时使用最新版的Photoshop插件的功能，带来不好体验。SD-PPP节点开发人员，是非常有负责任心的，社区和群里面体验者有反馈BUG或者建议功能，第一时间去修复BUG或更新功能，所以更新频率非常高，在此给SD-PPP节点开发人员大大点赞！！！

CCXManag辅助节点很好解决小伙伴的使用SD-PPP节点升级后痛点，CCXManag设置完运行一次，插件自动记忆你设置的信息，下次重启COMFYUI自动运行CCXManag节点，保证无论是否SD-PPP节点有升级，Photoshop插件都是同步更新的，使用CCXManag节点的小伙伴，你们完全可以忽略再去Photoshop更新插件了。

CCXManag节点添加了可视化功能：节点运行后在COMFYUI控制台，可以查到CCXManag节点运行的信息，运行是否成功。

CCXManag节点支持SD-PPP节点1.0版本和2.0版本同时运行。

安装CCXManag节点前准备工作：
1. 已经安装Photoshop软件（版本大于24）
2. 已经安装最新版的SD-PPP节点
3. Photoshop安装目录找到Plug-ins，在Plug-ins文件夹里面新建两个新文件夹，分别命名：sd-ppp_PS和sd-ppp2_PS（注意：之前有安装SD-PPP插件的文件夹，请删除）准备分别复制sd-ppp_PS和sd-ppp2_PS路径使用
4. SD-PPP节点安装目录下找到static文件夹，准备复制static路径使用

安装CCXManag节点：

方法一：Git Clone（推荐）
cd ComfyUI/custom_nodes
git clone https://github.com/WWWEN8/SDPPPautoupdate.git

方法二：手动下载
下载本项目的ZIP文件
解压到 ComfyUI/custom_nodes/
确保文件夹结构正确

方法三：ComfyUI Manager
如果已收录到ComfyUI Manager，可直接搜索"CCXManag"安装

CCXManage is an auxiliary plugin specifically developed for the SD-PPP plugin.

Users who have previously used the SD-PPP node found it very troublesome. The SD-PPP node has been upgraded, and installing the plugin manually in Photoshop is quite complex, which prevents the SD-PPP from using the latest Photoshop plugin features in a timely manner, leading to a poor user experience. The developers of the SD-PPP node are highly responsible, as they promptly fix bugs or update features based on feedback from testers in the community and groups. Therefore, the update frequency is very high. Here, a big thumbs-up to the SD-PPP node developers!!!

The CCXManage auxiliary node effectively addresses the pain points of users who have upgraded the SD-PPP node. After setting up CCXManage and running it once, the plugin automatically memorizes your settings. The next time COMFYUI restarts, it will automatically run the CCXManage node, ensuring that the Photoshop plugin is always synchronized with the latest updates, regardless of whether the SD-PPP node has been upgraded. CCXManag node users, you can completely ignore updating the plugin in Photoshop.

The CCXManag node has added a visual feature: after the node runs, you can check the CCXManage node running information in the COMFYUI console to see if it ran successfully.

The CCXManag node supports both versions 1.0 and 2.0 of the SD-PPP node simultaneously.

Prerequisites for installing and using the CCXManag node:
1. Photoshop software has already been installed (version greater than 24).
2. The latest version of the SD-PPP node has been installed.
3. In the Photoshop installation directory, find the Plug-ins folder and create two new folders inside it, naming them: sd-ppp_PS and sd-ppp2_PS.
4. In the SD-PPP node installation directory, find the static folder and prepare to use its path.

Installing the CCXManag node:

Method 1: Git Clone (Recommended)
cd ComfyUI/custom_nodes
git clone https://github.com/WWWEN8/SDPPPautoupdate.git

Method 2: Manual Download
Download the ZIP file for this project
Extract it to ComfyUI/custom_nodes/
Ensure the folder structure is correct

Method 3: ComfyUI Manager
If it has been included in the ComfyUI Manager, you can directly search for "CCXManag" to install it.

<img width="1388" height="981" alt="5e1d3fb9-3c1b-4cdd-a2d2-b2c785466a5e" src="https://github.com/user-attachments/assets/843c6343-9f2b-418e-9f31-2de4137bf57f" />

source_path输入：
static文件路径，如：
<img width="1069" height="415" alt="1b5addcf-5bfc-4d5f-b6ab-179fd8630a5c" src="https://github.com/user-attachments/assets/7eb154f7-2a55-4f10-87ff-3146d83a2036" />

target_path输入：
1.SDPPP插件自动更新助手1.0节点输入：sd-ppp_PS文件路径，如：
<img width="700" height="285" alt="9408e409-d9f0-42da-a136-c4dd6da0e567" src="https://github.com/user-attachments/assets/0fc25307-fbf0-4ff8-93b5-05f71a1c1cd7" />
2.SDPPP插件自动更新助手2.0节点输入：sd-ppp2_PS文件路径，如：
<img width="745" height="234" alt="9eeecf46-a559-459f-bd41-dbde4710cee0" src="https://github.com/user-attachments/assets/853c2302-e414-4dc4-85cf-519b98144d6c" />



