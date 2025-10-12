"""
ComfyUI-CCXManager - SD-PPP插件更新助手
专门为SD-PPP插件开发的辅助节点，自动管理和更新Photoshop侧插件
"""

from .ccx_downloader_node import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
__version__ = "1.0.0"

# 可选：添加Web目录支持（如果有JS组件）
# WEB_DIRECTORY = "web"
