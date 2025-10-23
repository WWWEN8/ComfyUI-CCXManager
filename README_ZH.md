# ComfyUI-CCXManager

<div align="center">
<img width="1580" height="969" alt="CH-2" src="https://github.com/user-attachments/assets/f030d01b-82c0-4472-b47d-6fb58fa1be76" />
<br>
  <p><strong>SD-PPP插件更新助手 - 自动管理Photoshop侧插件更新</strong></p>
</div>
### 工作流(https://github.com/WWWEN8/ComfyUI-CCXManager/blob/d4d885a66f463f66620852b3d95afee34b485599/workflows/SD-PPP%E6%8F%92%E4%BB%B6%E6%9B%B4%E6%96%B0%E5%8A%A9%E6%89%8B-%E6%94%AF%E6%8C%81PS%E6%93%8D%E4%BD%9C.png)

CCXManage是专门为SD-PPP插件开发的一个辅助节点。

之前用过SD-PPP节点的小伙伴都感觉非常困扰，SD-PPP节点ComfyUI侧升级了，另外Photoshop侧还要比较复杂去手动去安装插件，造成SD-PPP不能及时使用最新版的Photoshop侧插件的功能，带来不好体验。尤其SD-PPP节点更新频率非常高，因为SD-PPP节点开发人员，为了更好完善节点，社区和群里面体验者有反馈BUG或者建议功能，第一时间去努力修复BUG或更新功能，在此给SD-PPP节点开发人员大大点赞！！！

- ✅ 自动记忆设置信息，重启ComfyUI自动检测SD-PPP更新
- ✅ 支持SD-PPP节点1.0版本和2.0版本同时运行
- ✅ 支持网站下载CCX进行更新
- ✅ 具备智能检测功能，仅在SD-PPP有更新时运行.
- ✅ 提供可视化运行信息，在ComfyUI控制台显示运行状态
- ✅ 添加Comfyui侧自动更新SDPPP节点（新）
  
> **注意：** 只支持本地部署的ComfyUI，不支持云端ComfyUI.

## 🛠️ 安装条件

1. 已安装Photoshop软件（版本≥24）
2. ComfyUI侧已安装最新版的SD-PPP节点
3. 在Photoshop插件目录下创建两个文件夹：`sd-ppp_PS`和`sd-ppp2_PS`

## 📦 安装方法

### 方法一：通过ComfyUI Manager安装
在ComfyUI Manager中搜索"ComfyUI-CCXManager"并安装

### 方法二：Git Clone（推荐）
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/WWWEN8/ComfyUI-CCXManager.git
```

### 方法三：手动安装
1. 下载本项目的ZIP文件
2. 解压到`ComfyUI/custom_nodes/`目录下
3. 重启ComfyUI

## 🚀 使用说明

CCXManag节点有三个节点：
Photoshop side automatic update SDPPP2.0/
Photoshop side automatic update SDPPp1.0/
Comfyui side automatic update SDPPP

### source_type选择输入：

1. url：（推荐）网络下载，默认即可

2. local_path ：本地.CCX文件安装，.CCX文件一般在SD-PPP安装目录下的static文件夹里面，复制.CCX路径在target_path框里面即可，不推荐

例子：

Photoshop side automatic update SDPPp1.0：target_path框填写对应是“H:\ComfyUI\custom_nodes\sd-ppp\static\sd-ppp_PS.ccx”注意路径结尾是sd-ppp_PS.ccx

Photoshop side automatic update SDPPp2.0：target_path框填写对应是“H:\ComfyUI\custom_nodes\sd-ppp\static\sd-ppp2_PS.ccx”注意路径结尾是sd-ppp2_PS.ccx

### source_path输入：

输入.CCX下载网站，保持默认下载的网站，不用修改

1. Photoshop side automatic update SDPPp1.0，节点默认网站：https://gitee.com/zombieyang/sd-ppp/raw/main/static/sd-ppp_PS.ccx
 
2. Photoshop side automatic update SDPPp2.0，节点默认网站：https://gitee.com/zombieyang/sd-ppp/raw/main/static/sd-ppp2_PS.ccx

### target_path输入：

1.Photoshop side automatic update SDPPp1.0，输入：sd-ppp_PS文件路径，如：

<img width="700" height="285" alt="9408e409-d9f0-42da-a136-c4dd6da0e567" src="https://github.com/user-attachments/assets/3f478c7e-8d20-4f96-beab-9f4e9cf8e63d" />

2.Photoshop side automatic update SDPPp2.0，输入：sd-ppp2_PS文件路径，如：

<img width="745" height="234" alt="9eeecf46-a559-459f-bd41-dbde4710cee0" src="https://github.com/user-attachments/assets/0cb971ab-2548-457a-bf54-30ba40bf8930" />

### github_repo_url 输入：

检测有最新更新github仓库更新，仓库网址输入。检测到SD-PPP侧节点一旦有更新情况下，激活重启ComfyUI运行CCXManag自动更新。没更新情况，重启不会运行CCXManag进行更新。保持默认，不要修改

默认SD-PPP节点仓库：https://github.com/zombieyang/sd-ppp.git

### auto_run_on_restart选择输入：

enable代表开启，重启ComfyUI自动运行，开启了Photoshop插件同步更新功能。（默认）

disable代表禁用，重启ComfyUI节点不会运行，关闭了Photoshop插件同步更新功能。

enable开启后，要运行一次，才能生效，下次重启ComfyUI，Photoshop插件自动同步更新（disable禁用同理）

运行节点后控制台，会显示运行信息如下（ComfyUI重启后也会看到控制台运行信息）
<img width="992" height="199" alt="93a36210-5723-4959-bd90-ebb561810540" src="https://github.com/user-attachments/assets/cc375204-2c64-416b-91b8-b4d96b4cf710" />
到Photoshop软件查看插件是否安装成功

### 注意事项：
1. SDPPP插件更新助手1.0最新节点，target_path对应是“sd-ppp_PS文件路径”

2. SDPPP插件更新助手2.0最新节点，target_path对应是“sd-ppp2_PS文件路径”

3. 若安装路径改变，重新在节点设置改变后的路径，运行节点后生效

4. CCXManage节点有功能更新，导致失效，请按节点填写要求重新设置输入
 
5. 检查SD-PPP节点更新，需要开启代理网络才能使用；没有代理网络可以尝试local_path本地CCX文件来设置代替

6. 安装路径谨慎选择，更新时会把路径的文件里面内容清空。不要随便输入安装路径进行操作，避免误删重要文件

## 👨‍💻 开发者信息

- 作者：WWWEN8
- GitHub：[https://github.com/WWWEN8/ComfyUI-CCXManager](https://github.com/WWWEN8/ComfyUI-CCXManager)
- 问题反馈：请在GitHub仓库提交Issue

## 📄 许可证

此项目采用MIT许可证 - 详情请查看[LICENSE](LICENSE)文件

















