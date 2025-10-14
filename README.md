# ComfyUI-CCXManager

<div align="center">
  <img src="https://github.com/user-attachments/assets/dcc7d4e1-d71a-452b-ba59-612c8a5ef340" alt="CCXManager node interface" width="700">
  <br>
  <p><strong>SD-PPP Plugin Update Assistant - Automatically manages Photoshop-side plugin updates</strong></p>
</div>

CCXManage is an auxiliary node specifically developed for the SD-PPP plugin.

Users who have previously used the SD-PPP node found it very troublesome. When the ComfyUI side of the SD-PPP node was upgraded, the Photoshop side required a more complex manual installation of the plugin, causing the SD-PPP to not be able to use the latest features of the Photoshop-side plugin in a timely manner, resulting in a poor experience. Especially since the SD-PPP node is updated at a very high frequency, because the SD-PPP node developers, in order to better improve the node, receive feedback on BUGs or suggested features from the community and group testers, and they work hard to fix BUGs or update features at the first opportunity. A big thumbs up to the SD-PPP node developers!!!

- ✅ Automatically remembers settings and restarts ComfyUI to automatically detect SD-PPP updates
- ✅ Supports running both SD-PPP node version 1.0 and version 2.0 simultaneously
- ✅ Supports downloading CCX from websites for updates
- ✅ Has intelligent detection functionality, only runs when SD-PPP has updates
- ✅ Provides visual operation information, displaying operation status in the ComfyUI console

> **Note:** Only supports locally deployed ComfyUI, not cloud-based ComfyUI.

## 🛠️ Installation Requirements

1. Photoshop software installed (version ≥ 24)
2. The latest version of the SD-PPP node installed on the ComfyUI side
3. Create two folders in the Photoshop plugin directory: `sd-ppp_PS` and `sd-ppp2_PS`

## 📦 Installation Methods

### Method 1: Install via ComfyUI Manager
Search for "ComfyUI-CCXManager" in ComfyUI Manager and install it

### Method 2: Git Clone (Recommended)
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/WWWEN8/ComfyUI-CCXManager.git
```

### Method 3: Manual Installation
1. Download the ZIP file of this project
2. Extract it to the `ComfyUI/custom_nodes/` directory
3. Restart ComfyUI

## 🚀 Usage Instructions

The CCXManage node has two nodes: SDPPP Plugin Update Assistant 1.0 Latest and SDPPP Plugin Update Assistant 2.0 Latest

### source_type selection input:

1. url: (Recommended) Network download, default is fine

2. local_path: Install local .CCX file, .CCX file is usually in the static folder under the SD-PPP installation directory, copy the .CCX path to the target_path box, not recommended

Example:

SDPPP Plugin Update Assistant 1.0 Latest node: Fill in "H:\ComfyUI\custom_nodes\sd-ppp\static\sd-ppp_PS.ccx" in the target_path box, note that the path ends with sd-ppp_PS.ccx

SDPPP Plugin Update Assistant 2.0 Latest node: Fill in "H:\ComfyUI\custom_nodes\sd-ppp\static\sd-ppp2_PS.ccx" in the target_path box, note that the path ends with sd-ppp2_PS.ccx

### source_path input:

Input the .CCX download website, keep the default download website, no need to modify

1. SDPPP Plugin Update Assistant 1.0 Latest, node default website: https://gitee.com/zombieyang/sd-ppp/raw/main/static/sd-ppp_PS.ccx
 
2. SDPPP Plugin Update Assistant 2.0 Latest, node default website: https://gitee.com/zombieyang/sd-ppp/raw/main/static/sd-ppp2_PS.ccx

### target_path input:

1. SDPPP Plugin Update Assistant 1.0 Latest node, input: sd-ppp_PS file path, such as:

<img width="700" height="285" alt="9408e409-d9f0-42da-a136-c4dd6da0e567" src="https://github.com/user-attachments/assets/3f478c7e-8d20-4f96-beab-9f4e9cf8e63d