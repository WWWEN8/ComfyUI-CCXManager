import os
import shutil
import json
import zipfile
import requests
from datetime import datetime
from urllib.parse import urlparse

class CCXManagerNode:
    # 修复1: 添加配置文件名参数
    def __init__(self, config_filename="config.json"):
        self.config_path = os.path.join(os.path.dirname(__file__), config_filename)
        self.config = self.load_config()
        self.status = "未运行"
        self.temp_dir = os.path.join(os.path.dirname(__file__), "temp")
        # 创建临时目录
        os.makedirs(self.temp_dir, exist_ok=True)

    def load_config(self):
        """加载配置文件，如果不存在则创建默认配置"""
        default_config = {
            "source_path": "",
            "target_path": "",
            "ccx_filename": "",
            "auto_run_on_restart": False,
            "last_run_time": ""
        }
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4, ensure_ascii=False)
                return default_config
        except Exception as e:
            self.status = f"加载配置失败: {str(e)}"
            print(f"[CCXManager] 加载配置失败: {str(e)}")
            return default_config

    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.status = f"保存配置失败: {str(e)}"
            print(f"[CCXManager] 保存配置失败: {str(e)}")

    def download_from_url(self, url):
        """从URL下载CCX文件并返回本地临时路径"""
        try:
            # 添加时间戳参数
            timestamp = int(datetime.now().timestamp() * 1000)
            if '?' in url:
                url += f"&_={timestamp}"
            else:
                url += f"?_={timestamp}"
              
            # 发送请求
            print(f"[CCXManager] 开始下载: {url}")
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
              
            # 获取文件名
            filename = os.path.basename(urlparse(url).path)
            if not filename.endswith('.ccx'):
                self.status = "URL不是有效的CCX文件"
                return None, None
              
            temp_path = os.path.join(self.temp_dir, filename)
              
            # 保存文件
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
              
            print(f"[CCXManager] 下载完成: {temp_path}")
            return temp_path, filename
        except Exception as e:
            self.status = f"下载失败: {str(e)}"
            print(f"[CCXManager] 下载失败: {str(e)}")
            return None, None

    def unzip_ccx(self, source_path, target_path):
        """解压CCX文件到目标路径"""
        try:
            with zipfile.ZipFile(source_path, 'r') as zip_ref:
                zip_ref.extractall(target_path)
            return True
        except Exception as e:
            self.status = f"解压失败: {str(e)}"
            print(f"[CCXManager] 解压失败: {str(e)}")
            return False

    def clean_temp_files(self):
        """清理临时文件"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                os.makedirs(self.temp_dir, exist_ok=True)
        except Exception as e:
            print(f"[CCXManager] 清理临时文件失败: {str(e)}")

    def run(self, source_path, target_path, auto_run=False):
        """执行CCX文件处理流程"""
        self.status = "处理中"
        self.config["source_path"] = source_path
        self.config["target_path"] = target_path
        self.config["auto_run_on_restart"] = auto_run
        self.config["last_run_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_config()

        # 验证目标路径
        if not target_path:
            self.status = "错误: 目标路径未设置"
            return self.status
        os.makedirs(target_path, exist_ok=True)

        # 清空目标文件夹内容
        try:
            if os.path.exists(target_path):
                for item in os.listdir(target_path):
                    item_path = os.path.join(target_path, item)
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
            print(f"[CCXManager] 目标文件夹已清空: {target_path}")
        except Exception as e:
            self.status = f"清理目标文件夹失败: {str(e)}"
            print(f"[CCXManager] 清理目标文件夹失败: {str(e)}")
            return self.status

        # 处理URL下载
        local_path = source_path
        ccx_filename = None
        is_url = source_path.startswith(('http://', 'https://'))

        if is_url:
            local_path, ccx_filename = self.download_from_url(source_path)
            if not local_path:
                return self.status
        else:
            # 验证本地文件
            if not os.path.exists(local_path):
                self.status = "错误: 源文件不存在"
                return self.status
            ccx_filename = os.path.basename(local_path)

        # 解压文件
        if self.unzip_ccx(local_path, target_path):
            self.status = f"成功: {ccx_filename} 已解压到 {target_path}"
        else:
            self.status = f"失败: 无法解压 {ccx_filename}"

        # 清理临时文件
        if is_url:
            self.clean_temp_files()

        print(f"[CCXManager] {self.status}")
        return self.status

    def auto_run(self):
        """重启后自动运行"""
        if self.config.get("auto_run_on_restart", False):
            print(f"[CCXManager] 检测到自动运行配置，正在执行CCX更新...")
            if all([self.config.get("source_path"), self.config.get("target_path")]):
                self.run(self.config["source_path"], self.config["target_path"], auto_run=self.config["auto_run_on_restart"])
            else:
                print(f"[CCXManager] 自动运行失败: 配置不完整")
        else:
            print(f"[CCXManager] 自动运行已禁用")

# 主节点
class CCXManager:
    @classmethod
    def INPUT_TYPES(s):
        # 加载配置以获取保存的target_path
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        default_target_path = ""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    default_target_path = config.get("target_path", "")
        except Exception as e:
            print(f"[CCXManager] 加载配置失败: {str(e)}")

        return {
            "required": {
                "source_type": (["local_path", "url"], {"default": "url"}),
                "source_path": ("STRING", {"default": "https://gitee.com/zombieyang/sd-ppp/raw/main/static/sd-ppp2_PS.ccx", "placeholder": "本地文件路径或URL"}),
                "target_path": ("STRING", {"default": default_target_path, "placeholder": "目标解压路径，例如：i:/311/ComfyUI/custom_nodes"}),
                "auto_run_on_restart": (["enable", "disable"], {"default": "enable"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("运行状态",)
    FUNCTION = "process_ccx"
    CATEGORY = "SD-PPP插件更新"
    TITLE = "SDPPP插件更新助手2.0最新"

    def __init__(self):
        self.manager = CCXManagerNode()

    def process_ccx(self, source_type, source_path, target_path, auto_run_on_restart):
        auto_run = auto_run_on_restart == "enable"
        # 根据源类型处理
        if source_type == "url" and not source_path.startswith(('http://', 'https://')):
            return ("错误: URL格式不正确",)
        status = self.manager.run(source_path, target_path, auto_run)
        return (status,)

# 分身节点
class CCXManagerCopy:
    @classmethod
    def INPUT_TYPES(s):
        # 加载配置以获取保存的target_path
        config_path = os.path.join(os.path.dirname(__file__), "config_copy.json")
        default_target_path = ""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    default_target_path = config.get("target_path", "")
        except Exception as e:
            print(f"[CCXManagerCopy] 加载配置失败: {str(e)}")

        return {
            "required": {
                "source_type": (["local_path", "url"], {"default": "url"}),
                "source_path": ("STRING", {"default": "https://gitee.com/zombieyang/sd-ppp/raw/main/static/sd-ppp_PS.ccx", "placeholder": "本地文件路径或URL"}),
                "target_path": ("STRING", {"default": default_target_path, "placeholder": "目标解压路径，例如：i:/311/ComfyUI/custom_nodes"}),
                "auto_run_on_restart": (["enable", "disable"], {"default": "enable"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("运行状态",)
    FUNCTION = "process_ccx"
    CATEGORY = "SD-PPP插件更新"
    TITLE = "SDPPP插件更新助手1.0最新"

    def __init__(self):
        # 使用独立配置文件
        self.manager = CCXManagerNode(config_filename="config_copy.json")

    def process_ccx(self, source_type, source_path, target_path, auto_run_on_restart):
        auto_run = auto_run_on_restart == "enable"
        if source_type == "url" and not source_path.startswith(("http://", "https://")):
            return ("错误: URL格式不正确",)
        status = self.manager.run(source_path, target_path, auto_run)
        return (status,)

# 节点注册
NODE_CLASS_MAPPINGS = {
    "CCXManager": CCXManager,
    "CCXManagerCopy": CCXManagerCopy
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CCXManager": "SDPPP插件更新助手2.0最新",
    "CCXManagerCopy": "SDPPP插件更新助手1.0最新"
}

# 程序启动时自动检查并运行
print(f"[CCXManager] SDPPP插件更新助手节点已加载")
# 主节点自动运行检查
manager = CCXManagerNode()
manager.auto_run()
# 克隆节点自动运行检查
manager_copy = CCXManagerNode(config_filename="config_copy.json")
manager_copy.auto_run()