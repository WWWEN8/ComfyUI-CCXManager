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


<img width="1388" height="981" alt="5e1d3fb9-3c1b-4cdd-a2d2-b2c785466a5e" src="https://github.com/user-attachments/assets/843c6343-9f2b-418e-9f31-2de4137bf57f" />

source_path输入：

static文件路径，如：
<img width="1069" height="415" alt="1b5addcf-5bfc-4d5f-b6ab-179fd8630a5c" src="https://github.com/user-attachments/assets/7eb154f7-2a55-4f10-87ff-3146d83a2036" />

target_path输入：

1.SDPPP插件自动更新助手1.0节点输入：sd-ppp_PS文件路径，如：
<img width="700" height="285" alt="9408e409-d9f0-42da-a136-c4dd6da0e567" src="https://github.com/user-attachments/assets/0fc25307-fbf0-4ff8-93b5-05f71a1c1cd7" />

2.SDPPP插件自动更新助手2.0节点输入：sd-ppp2_PS文件路径，如：
<img width="745" height="234" alt="9eeecf46-a559-459f-bd41-dbde4710cee0" src="https://github.com/user-attachments/assets/853c2302-e414-4dc4-85cf-519b98144d6c" />

ccx_filename输入选择保持默认即可

auto_run_on_restart选择输入：

1. enable代表开启，重启COMFYUI自动运行，开启了Photoshop插件同步更新功能。（默认）

2. disable代表禁用，重启COMFYUI节点不会运行，关闭了Photoshop插件同步更新功能。


输入完路径参数，运行后，控制台会显示运行信息，如下表示成功了。

enable开启，下次重启COMFYUI，控制台也会显示运行信息。

<img width="1520" height="1045" alt="16d757b7-8e4e-4859-a3f3-c3deaa72240b" src="https://github.com/user-attachments/assets/9bde7925-ed34-4c0e-a5b3-c2e09e0406a4" />

<img width="1321" height="265" alt="fb653b8b-13e8-4666-a93d-6fb08c91d3a1" src="https://github.com/user-attachments/assets/03125652-5bc0-45ec-bc1d-a7d62799c35c" />

disable选择禁用后，要运行节点一次，才能生效，重启COMFYUI控制台也会显示运行信息（enable开启同理）：

<img width="561" height="76" alt="7f3993e0-7934-4b50-ae73-15401ec38699" src="https://github.com/user-attachments/assets/a0e2e353-0995-4268-b9fb-652c1709f9ba" />

注意：
1. SDPPP插件自动更新助手1.0节点，target_path对应是“sd-ppp_PS文件路径”

2.SDPPP插件自动更新助手2.0节点，target_path对应是“sd-ppp2_PS文件路径”

3. SDPPP插件自动更新助手1.0节点和SDPPP插件自动更新助手2.0节点，source_path对应都是“static文件路径'

