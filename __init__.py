"""
ComfyUI-CCXManager - SD-PPP插件更新助手
专门为SD-PPP插件开发的辅助节点，自动管理和更新Photoshop侧插件
"""

from .ccx_downloader_node import NODE_CLASS_MAPPINGS as CCX_NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS as CCX_NODE_DISPLAY_NAME_MAPPINGS
from .auto_updater_node import NODE_CLASS_MAPPINGS as AUTO_NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS as AUTO_NODE_DISPLAY_NAME_MAPPINGS, auto_check_for_repo_updates
from .py.lgutils import NODE_CLASS_MAPPINGS as CCX_GROUP_EXECUTOR_NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS as CCX_GROUP_EXECUTOR_NODE_DISPLAY_NAME_MAPPINGS
from .node_version_manager import NODE_CLASS_MAPPINGS as VERSION_NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS as VERSION_NODE_DISPLAY_NAME_MAPPINGS

# 合并节点映射
NODE_CLASS_MAPPINGS = {**CCX_NODE_CLASS_MAPPINGS, **AUTO_NODE_CLASS_MAPPINGS, **CCX_GROUP_EXECUTOR_NODE_CLASS_MAPPINGS, **VERSION_NODE_CLASS_MAPPINGS}
NODE_DISPLAY_NAME_MAPPINGS = {**CCX_NODE_DISPLAY_NAME_MAPPINGS, **AUTO_NODE_DISPLAY_NAME_MAPPINGS, **CCX_GROUP_EXECUTOR_NODE_DISPLAY_NAME_MAPPINGS, **VERSION_NODE_DISPLAY_NAME_MAPPINGS}

__version__ = "3.8"
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']

# 版本更新记录
# v3.8: 将Comfyui side automatic update SD-PPP节点功能合并到SDPPP1.0和SDPPP2.0节点中，移除了enable update和sdppp_version选项
# v3.7: 优化PS侧节点，实现选择local_path时自动填充正确的ccx文件路径

# 可选：添加Web目录支持（如果有JS组件）
WEB_DIRECTORY = "web"

# 在后台线程中运行自动更新检查（延迟5秒）
import threading
timer = threading.Timer(5.0, auto_check_for_repo_updates)
timer.daemon = True
timer.start()
