CCXManage是专门为SD-PPP插件开发的一个辅助节点。

之前用过SD-PPP节点的小伙伴都感觉非常麻烦，SD-PPP节点升级了，另外Photoshop还要比较复杂去手动去安装插件，造成SD-PPP不能及时使用最新版的Photoshop插件的功能，带来不好体验。尤其SD-PPP节点更新频率非常高，因为SD-PPP节点开发人员，为了更好完善节点，社区和群里面体验者有反馈BUG或者建议功能，第一时间去努力修复BUG或更新功能，在此给SD-PPP节点开发人员大大点赞！！！

CCXManag设置完运行一次，插件自动记忆你设置的信息，下次重启COMFYUI自动运行CCXManag节点，无论SD-PPP节点是否有升级，Photoshop插件照样同步更新。使用CCXManag节点，完全摆脱手动去Photoshop更新插件了。

CCXManag节点添加了可视化功能：节点运行后在COMFYUI控制台，可以查到CCXManag节点运行的信息。

CCXManag节点支持SD-PPP节点1.0版本和2.0版本同时运行。

CCXManag只本地部署的COMFYUI，不支持云端的COMFYUI。这是下一步开发计划。。。

安装CCXManag节点准备下面条件：
1. 已经安装Photoshop软件（版本大于24）
2. 已经安装最新版的SD-PPP节点
3. Photoshop安装目录找到Plug-ins，在Plug-ins文件夹里面新建两个新文件夹，分别命名为：sd-ppp_PS和sd-ppp2_PS。（之前有安装过SD-PPP插件的文件夹，请删除）准备分别复制sd-ppp_PS和sd-ppp2_PS两个路径，等待粘贴

安装CCXManag节点：

方法一：Git Clone（推荐）

cd ComfyUI/custom_nodes

git clone https://github.com/WWWEN8/ComfyUI-CCXManager.git

方法二：手动下载
下载本项目的ZIP文件
解压到 ComfyUI/custom_nodes/

确保文件夹结构正确

方法三：ComfyUI Manager
如果已收录到ComfyUI Manager，可直接搜索"CCXManag"安装

CCXManag节点有两个节点：SDPPP插件更新助手1.0最新和SDPPP插件更新助手2.0最新

<img width="798" height="536" alt="aca82b8f-3170-4c15-a949-db6e3f39c109" src="https://github.com/user-attachments/assets/02209b4d-ba3e-4d60-b598-26c60ba76797" />

source_type选择输入：

1. url：（推荐）网络下载，默认即可

2. local_path ：本地.CCX文件安装，.CCX文件一般在SD-PPP安装目录下的static文件夹里面，复制.CCX路径在target_path框里面即可，不推荐

例子：

SDPPP插件更新助手1.0最新节点，target_path框填写对应是“H:\ComfyUI\custom_nodes\sd-ppp\static\sd-ppp_PS.ccx”注意路径结尾是sd-ppp_PS.ccx

SDPPP插件更新助手2.0最新节点，target_path框填写对应是“H:\ComfyUI\custom_nodes\sd-ppp\static\sd-ppp2_PS.ccx”注意路径结尾是sd-ppp2_PS.ccx

source_path输入：

输入.CCX下载网站，保持默认下载的网站，不用修改

target_path输入：

1.SDPPP插件更新助手1.0最新节点，输入：sd-ppp_PS文件路径，如：

<img width="700" height="285" alt="9408e409-d9f0-42da-a136-c4dd6da0e567" src="https://github.com/user-attachments/assets/3f478c7e-8d20-4f96-beab-9f4e9cf8e63d" />

2.SDPPP插件更新助手2.0最新节点，输入：sd-ppp2_PS文件路径，如：

<img width="745" height="234" alt="9eeecf46-a559-459f-bd41-dbde4710cee0" src="https://github.com/user-attachments/assets/0cb971ab-2548-457a-bf54-30ba40bf8930" />

auto_run_on_restart选择输入：

enable代表开启，重启COMFYUI自动运行，开启了Photoshop插件同步更新功能。（默认）

disable代表禁用，重启COMFYUI节点不会运行，关闭了Photoshop插件同步更新功能。

enable开启后，要运行一次，才能生效，下次重启COMFYUI，Photoshop插件自动同步更新（disable禁用同理）

<img width="1008" height="707" alt="8c9c9018-c033-4827-a063-33cbb718b2ff" src="https://github.com/user-attachments/assets/cafcc473-101b-4810-bb32-b6624cac8228" />

运行节点后控制台，会显示运行信息如下（COMFYUI重启后也会看到控制台运行信息）：

<img width="1030" height="243" alt="1d9eeacc-8523-4dd4-aa72-ded64197df8b" src="https://github.com/user-attachments/assets/a83df380-b835-4f1c-8eb1-298a6b5b93b5" />

到Photoshop软件查看插件是否安装成功

注意事项：
1. SDPPP插件更新助手1.0最新节点，target_path对应是“sd-ppp_PS文件路径”

2. SDPPP插件更新助手2.0最新节点，target_path对应是“sd-ppp2_PS文件路径”

3. 若安装路径改变，重新在节点设置改变后的路径，运行节点后生效

4. CCXManage节点有功能更新，导致失效，请按节点填写要求重新设置输入

