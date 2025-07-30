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
git clone https://github.com/your-username/put-tools.git

Method 2: Manual Download
Download the ZIP file for this project
Extract it to ComfyUI/custom_nodes/
Ensure the folder structure is correct

Method 3: ComfyUI Manager
If it has been included in the ComfyUI Manager, you can directly search for "CCXManag" to install it.

Method for using the CCXManag node:
