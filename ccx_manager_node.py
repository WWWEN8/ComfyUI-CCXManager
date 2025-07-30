import os
import shutil
import json
import zipfile
from datetime import datetime

class CCXManagerNode:
    def __init__(self, config_filename="config.json"):
        self.config_path = os.path.join(os.path.dirname(__file__), config_filename)
        self.config = self.load_config()
        self.status = "未运行"

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
        """保存当前配置到文件"""
        try:
            self.config["last_run_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            self.status = f"配置已保存: {self.config['last_run_time']}"
            print(f"[CCXManager] 配置已保存: {self.config['last_run_time']}")
        except Exception as e:
            self.status = f"保存配置失败: {str(e)}"
            print(f"[CCXManager] 保存配置失败: {str(e)}")

    def clear_directory(self, dir_path):
        """清空目标目录"""
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"[CCXManager] 创建目标目录: {dir_path}")
            return True
        try:
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            print(f"[CCXManager] 已清空目录: {dir_path}")
            return True
        except Exception as e:
            self.status = f"清空目录失败: {str(e)}"
            print(f"[CCXManager] 清空目录失败: {str(e)}")
            return False

    def extract_ccx(self, ccx_path, target_dir):
        """解压CCX文件到目标目录"""
        try:
            with zipfile.ZipFile(ccx_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            print(f"[CCXManager] CCX文件解压成功: {ccx_path}")
            return True
        except Exception as e:
            self.status = f"解压失败: {str(e)}"
            print(f"[CCXManager] 解压失败: {str(e)}")
            return False

    def run(self, source_path=None, target_path=None, ccx_filename=None, auto_run_on_restart=None):
        """执行CCX文件复制和解压流程"""
        if source_path is None: source_path = self.config.get("source_path")
        if target_path is None: target_path = self.config.get("target_path")
        if ccx_filename is None: ccx_filename = self.config.get("ccx_filename")
        if auto_run_on_restart is not None:
            self.config["auto_run_on_restart"] = auto_run_on_restart

        # 将路径转换为绝对路径
        if source_path: source_path = os.path.abspath(source_path)
        if target_path: target_path = os.path.abspath(target_path)

        # 更新配置中的绝对路径
        self.config["source_path"] = source_path
        self.config["target_path"] = target_path
        self.config["ccx_filename"] = ccx_filename

        if not all([source_path, target_path, ccx_filename]):
            self.status = "错误: 路径或文件名不能为空"
            print(f"[CCXManager] {self.status}")
            return self.status

        ccx_source_path = os.path.join(source_path, ccx_filename)
        if not os.path.exists(ccx_source_path):
            self.status = f"错误: CCX文件不存在 - {ccx_source_path}"
            print(f"[CCXManager] {self.status}")
            return self.status

        if not self.clear_directory(target_path):
            return self.status

        try:
            ccx_target_path = os.path.join(target_path, ccx_filename)
            shutil.copy2(ccx_source_path, ccx_target_path)
            self.status = f"CCX文件已复制: {ccx_target_path}"
            print(f"[CCXManager] {self.status}")
        except Exception as e:
            self.status = f"复制文件失败: {str(e)}"
            print(f"[CCXManager] {self.status}")
            return self.status

        if self.extract_ccx(ccx_target_path, target_path):
            self.status = f"成功: CCX文件已解压到 {target_path}"
            print(f"[CCXManager] CCX文件已经全部更新")
            self.save_config()
        else:
            self.status = f"失败: {self.status}"

        return self.status

    def auto_run(self):
        """重启后自动运行"""
        if self.config.get("auto_run_on_restart", False):
            print(f"[CCXManager] 检测到自动运行配置，正在执行CCX更新...")
            if all([self.config.get("source_path"), self.config.get("target_path"), self.config.get("ccx_filename")]):
                self.run()
            else:
                print(f"[CCXManager] 自动运行失败: 配置不完整")
        else:
            print(f"[CCXManager] 自动运行已禁用")

class CCXManager:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "source_path": ("STRING", {"default": "", "placeholder": "CCX文件所在路径"}),
                "target_path": ("STRING", {"default": "", "placeholder": "目标解压路径"}),
                "ccx_filename": ("STRING", {"default": "sd-ppp_PS.ccx", "placeholder": "CCX文件名(含后缀)"}),
                "auto_run_on_restart": (["enable", "disable"], {"default": "enable"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("运行状态",)
    FUNCTION = "process_ccx"
    CATEGORY = "文件操作"
    TITLE = "SDPPP插件自动更新助手1.0"

    def __init__(self):
        self.manager = CCXManagerNode()

    def process_ccx(self, source_path, target_path, ccx_filename, auto_run_on_restart):
        auto_run = auto_run_on_restart == "enable"
        status = self.manager.run(source_path, target_path, ccx_filename, auto_run)
        return (status,)

class CCXManagerCopy:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "source_path": ("STRING", {"default": "", "placeholder": "CCX文件所在路径"}),
                "target_path": ("STRING", {"default": "", "placeholder": "目标解压路径"}),
                "ccx_filename": ("STRING", {"default": "sd-ppp2_PS.ccx", "placeholder": "CCX文件名(含后缀)"}),
                "auto_run_on_restart": (["enable", "disable"], {"default": "enable"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("运行状态",)
    FUNCTION = "process_ccx"
    CATEGORY = "文件操作"
    TITLE = "SDPPP插件自动更新助手2.0"

    def __init__(self):
        self.manager = CCXManagerNode(config_filename="config_copy.json")

    def process_ccx(self, source_path, target_path, ccx_filename, auto_run_on_restart):
        auto_run = auto_run_on_restart == "enable"
        status = self.manager.run(source_path, target_path, ccx_filename, auto_run)
        return (status,)

NODE_CLASS_MAPPINGS = {
    "CCXManager": CCXManager,
    "CCXManagerCopy": CCXManagerCopy
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CCXManager": "SDPPP插件自动更新助手1.0",
    "CCXManagerCopy": "SDPPP插件自动更新助手2.0"
}

# 程序启动时自动检查并运行所有节点
print(f"[CCXManager] SDPPP插件自动更新助手加载")

# 主节点自动运行
main_manager = CCXManagerNode()
main_manager.auto_run()

# 分身节点自动运行
clone_manager = CCXManagerNode(config_filename="config_copy.json")
clone_manager.auto_run()