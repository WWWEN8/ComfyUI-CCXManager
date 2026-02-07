import os
import shutil
import json
import zipfile
import requests
import hashlib
from datetime import datetime
from urllib.parse import urlparse

__version__ = "3.8"
# 更新说明：修复了auto_run_on_restart开关状态不同步的问题，现在日志显示会准确反映用户的实际设置

class CCXManagerNode:
    """CCX管理器核心类，负责配置加载、保存和自动运行检查"""
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
            "last_run_time": "",
            "github_repo_url": "https://github.com/zombieyang/sd-ppp.git",
            "last_commit_hash": "",
            "version": __version__,
            "force_reinstall_on_next_restart": False
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

    def get_github_latest_commit(self, repo_url):
        """获取GitHub仓库最新commit哈希值，支持多种URL格式和分支"""
        try:
            # 解析仓库路径和分支
            branch = "main"  # 默认分支

            # 处理不同格式的URL
            if repo_url.startswith('git@github.com:'):
                # SSH格式: git@github.com:owner/repo.git
                path = repo_url.replace('git@github.com:', '')
                if ':' in path:
                    # 包含分支: git@github.com:owner/repo.git:branch
                    path, branch = path.split(':', 1)
                owner, repo = path.split('/', 1)
                repo = repo.replace('.git', '')
            elif repo_url.startswith(('http://', 'https://')):
                # HTTP/HTTPS格式
                parsed_url = urlparse(repo_url)
                path_parts = parsed_url.path.strip('/').split('/')
                if len(path_parts) < 2:
                    return None
                owner, repo = path_parts[0], path_parts[1].replace('.git', '')
                # 检查URL中是否包含分支信息
                if len(path_parts) >= 4 and path_parts[2] == 'tree':
                    branch = path_parts[3]
            else:
                # 不支持的URL格式
                print(f"[CCXManager] 不支持的GitHub URL格式: {repo_url}")
                return None

            # 构建API URL
            api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"
            print(f"[CCXManager] 获取GitHub最新commit: {api_url}")

            # 发送请求
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            commit_data = response.json()
            return commit_data['sha']
        except Exception as e:
            print(f"[CCXManager] 获取GitHub最新commit失败: {str(e)}")
            return None

    def check_github_update(self):
        """检查GitHub仓库是否有更新"""
        repo_url = self.config.get("github_repo_url", "")
        if not repo_url:
            return False

        current_hash = self.config.get("last_commit_hash", "")
        latest_hash = self.get_github_latest_commit(repo_url)

        if not latest_hash:
            return False

        if current_hash != latest_hash:
            self.config["last_commit_hash"] = latest_hash
            self.save_config()
            return True
        return False

    def run(self, source_path, target_path, auto_run=False):
        """执行CCX文件处理流程"""
        self.status = "处理中"
        print(f"[CCXManager] 开始处理: {source_path} -> {target_path}")
        
        # 保存配置前进行路径验证
        self.config["source_path"] = source_path if source_path else ""
        self.config["target_path"] = target_path if target_path else ""
        self.config["auto_run_on_restart"] = auto_run
        self.config["last_run_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 设置下次重启强制安装标志
        if auto_run:
            self.config["force_reinstall_on_next_restart"] = True
            print(f"[CCXManager] 已设置下次重启强制安装标志")
        
        self.save_config()

        # 验证目标路径
        if not target_path:
            self.status = "错误: 目标路径未设置"
            print(f"[CCXManager] {self.status}")
            return self.status
        
        # 创建目标目录（确保存在）
        try:
            os.makedirs(target_path, exist_ok=True)
            print(f"[CCXManager] 确认目标目录存在: {target_path}")
        except Exception as mkdir_error:
            self.status = f"错误: 无法创建目标目录: {str(mkdir_error)}"
            print(f"[CCXManager] {self.status}")
            return self.status

        # 清空目标文件夹内容（添加更多错误处理）
        try:
            if os.path.exists(target_path):
                for item in os.listdir(target_path):
                    item_path = os.path.join(target_path, item)
                    try:
                        if os.path.isfile(item_path) or os.path.islink(item_path):
                            os.unlink(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    except Exception as item_error:
                        print(f"[CCXManager] 警告: 无法删除{item_path}: {str(item_error)}")
            print(f"[CCXManager] 目标文件夹已清空: {target_path}")
        except Exception as e:
            self.status = f"清理目标文件夹失败: {str(e)}"
            print(f"[CCXManager] 清理目标文件夹失败: {str(e)}")
            return self.status

        # 处理URL下载
        local_path = source_path
        ccx_filename = None
        is_url = source_path and source_path.startswith(('http://', 'https://'))

        if is_url:
            local_path, ccx_filename = self.download_from_url(source_path)
            if not local_path:
                return self.status
        else:
            # 验证本地文件
            if not local_path or not os.path.exists(local_path):
                self.status = "错误: 源文件不存在或路径无效"
                print(f"[CCXManager] {self.status}: {local_path}")
                return self.status
            ccx_filename = os.path.basename(local_path)

        # 解压文件
        if self.unzip_ccx(local_path, target_path):
            self.status = f"成功: {ccx_filename} 已解压到 {target_path}"
            print(f"[CCXManager] {self.status}")
        else:
            self.status = f"失败: 无法解压 {ccx_filename}"
            print(f"[CCXManager] {self.status}")

        # 清理临时文件
        if is_url:
            self.clean_temp_files()

        return self.status

    def auto_run(self):
        """重启后自动运行"""
        # 检查GitHub是否有更新
        has_update = self.check_github_update()
        auto_run_enabled = self.config.get("auto_run_on_restart", False)
        force_reinstall = self.config.get("force_reinstall_on_next_restart", False)

        # 执行条件：
        # 1. 自动运行已启用，且(检测到更新 或者 需要强制重新安装)
        if auto_run_enabled and (has_update or force_reinstall):
            print(f"[CCXManager] 自动运行已启用{', 且检测到更新' if has_update else ', 执行强制重新安装' if force_reinstall else ''}，正在执行CCX更新...")
            if all([self.config.get("source_path"), self.config.get("target_path")]):
                # 运行后保持用户的auto_run_on_restart设置不变
                result = self.run(self.config["source_path"], self.config["target_path"], auto_run=auto_run_enabled)
                
                # 执行完强制重新安装后，清除标志
                if force_reinstall:
                    self.config["force_reinstall_on_next_restart"] = False
                    self.save_config()
                    print(f"[CCXManager] 强制重新安装完成，已清除下次重启强制安装标志")
            else:
                print(f"[CCXManager] 自动运行失败: 配置不完整")
        else:
            if not auto_run_enabled:
                print(f"[CCXManager] 自动运行已禁用")
            else:
                print(f"[CCXManager] 没有检测到更新，忽略自动运行")

# 主节点
def get_auto_target_path(subfolder_name):
    """获取自动目标路径，如果存在基础目录配置则使用它并添加子文件夹"""
    config_dir_path = os.path.join(os.path.dirname(__file__), "config_dir.json")
    try:
        if os.path.exists(config_dir_path):
            with open(config_dir_path, 'r', encoding='utf-8') as f:
                dir_config = json.load(f)
                base_directory = dir_config.get("base_directory", "")
                if base_directory:
                    # 确保路径以Plug-ins结尾
                    normalized_base = base_directory.rstrip('\\/')
                    if not normalized_base.lower().endswith('\\plug-ins') and not normalized_base.lower().endswith('/plug-ins'):
                        normalized_base += '\\Plug-ins'
                    # 自动添加子文件夹路径，确保路径格式一致
                    target_path = os.path.normpath(os.path.join(normalized_base, subfolder_name))
                    print(f"[CCXManager] 为{subfolder_name}获取目标路径: {target_path}")
                    return target_path
                else:
                    print(f"[CCXManager] 基础目录配置为空，无法生成目标路径")
        else:
            print(f"[CCXManager] 配置文件不存在: {config_dir_path}")
            # 尝试创建默认配置
            try:
                default_config = {
                    "base_directory": "",
                    "auto_run_on_restart": True,
                    "last_run_time": "",
                    "version": __version__
                }
                with open(config_dir_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4, ensure_ascii=False)
                print(f"[CCXManager] 已创建默认配置文件: {config_dir_path}")
            except Exception as create_error:
                print(f"[CCXManager] 创建默认配置文件失败: {str(create_error)}")
    except Exception as e:
        print(f"[CCXManager] 读取目录配置失败: {str(e)}")
        # 尝试备份并重新创建配置
        try:
            backup_path = config_dir_path + ".bak"
            if os.path.exists(config_dir_path):
                shutil.copy2(config_dir_path, backup_path)
                print(f"[CCXManager] 已备份损坏的配置文件到: {backup_path}")
            
            default_config = {
                "base_directory": "",
                "auto_run_on_restart": True,
                "last_run_time": "",
                "version": __version__
            }
            with open(config_dir_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            print(f"[CCXManager] 已重新创建配置文件: {config_dir_path}")
        except Exception as recovery_error:
            print(f"[CCXManager] 恢复配置文件失败: {str(recovery_error)}")
    return ""

class CCXManager:
    @classmethod
    def INPUT_TYPES(s):
        # 加载配置
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        default_github_url = "https://github.com/zombieyang/sd-ppp.git"
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    default_github_url = config.get("github_repo_url", default_github_url)
        except Exception as e:
            print(f"[CCXManager] 加载配置失败: {str(e)}")

        return {
            "required": {
                "source_type": (["local_path", "url"], {"default": "url"}),
                "source_path": ("STRING", {"default": "https://gitee.com/zombieyang/sd-ppp/raw/main/static/sd-ppp2_PS.ccx", "placeholder": "本地文件路径或URL"}),
                "github_repo_url": ("STRING", {"default": default_github_url, "placeholder": "GitHub仓库URL，留空禁用更新检测"}),
                "auto_run_on_restart": (["enable", "disable"], {"default": "enable"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("Status", "Generated_Path")
    FUNCTION = "process_ccx"
    CATEGORY = "Update of SD-PPP Plugin"
    TITLE = "Photoshop side automatic update SDPPP2.0"

    def __init__(self):
        self.manager = CCXManagerNode()
        # 初始化SDPPP路径管理器的配置
        self.config_sdppp_path = os.path.join(os.path.dirname(__file__), "config_sdppp_path.json")

    def _get_custom_nodes_path(self):
        """自动获取custom_nodes路径"""
        # 获取当前文件所在目录的父目录（即custom_nodes目录）
        current_dir = os.path.dirname(__file__)
        # 获取父目录，即custom_nodes目录
        custom_nodes_path = os.path.dirname(current_dir)
        
        print(f"[CCXManager] 自动识别的custom_nodes路径: {custom_nodes_path}")
        return custom_nodes_path

    def _save_sdppp_path_config(self, enable_update=True):
        """保存SDPPP路径配置"""
        try:
            config = {
                "enable_update": enable_update,
                "last_run_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "version": __version__
            }
            with open(self.config_sdppp_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            print(f"[CCXManager] SDPPP路径配置已保存到: {self.config_sdppp_path}")
        except Exception as e:
            print(f"[CCXManager] 保存SDPPP路径配置失败: {str(e)}")

    def process_ccx(self, source_type, source_path, github_repo_url, auto_run_on_restart):
        auto_run = auto_run_on_restart == "enable"
        # 更新GitHub仓库URL配置
        self.manager.config["github_repo_url"] = github_repo_url
        
        # 自动获取目标路径
        target_path = get_auto_target_path("sd-ppp2_PS")
        if not target_path:
            return ("错误: 无法获取目标路径，请先使用Create SD-PPP installation directory节点设置基础路径", "")
        
        try:
            # 如果选择local_path，执行Comfyui side节点的功能
            generated_path = ""
            if source_type == "local_path":
                # 保存SDPPP路径配置
                self._save_sdppp_path_config(enable_update=True)
                
                # 自动获取custom_nodes路径
                custom_nodes_path = self._get_custom_nodes_path()
                
                # 验证custom_nodes_path是否存在
                if not os.path.exists(custom_nodes_path):
                    return (f"错误: 无法识别有效的custom_nodes目录: {custom_nodes_path}", "")
                
                # 生成对应的CCX文件路径
                generated_path = os.path.join(custom_nodes_path, "sd-ppp", "static", "sd-ppp2_PS.ccx")
                
                # 输出运行信息
                print(f"[CCXManager] 运行信息:")
                print(f"[CCXManager] - 版本: SDPPP2.0")
                print(f"[CCXManager] - 自动识别的custom_nodes路径: {custom_nodes_path}")
                print(f"[CCXManager] - 生成的CCX路径: {generated_path}")
                print(f"[CCXManager] - 更新开关: {'开启' if auto_run else '关闭'}")
                print(f"[CCXManager] - 目标节点: CCXManager")
                
                # 自动设置source_path
                source_path = generated_path
                print(f"[CCXManager] SDPPP2.0节点自动填充路径: {source_path}")
            
            # 确保保存源路径和目标路径到配置中，防止下一次运行时丢失
            self.manager.config["source_path"] = source_path
            self.manager.config["target_path"] = target_path
            self.manager.save_config()
            
            if source_type == "url" and not source_path.startswith(("http://", "https://")):
                return ("错误: URL格式不正确", "")
            
            # 验证目标路径是否存在，如果不存在则尝试创建
            if not os.path.exists(target_path):
                try:
                    os.makedirs(target_path, exist_ok=True)
                    print(f"[CCXManager] 已创建目标目录: {target_path}")
                except Exception as mkdir_error:
                    return (f"错误: 无法创建目标目录: {str(mkdir_error)}", "")
            
            status = self.manager.run(source_path, target_path, auto_run)
            return (status, generated_path)
        except Exception as e:
            error_msg = f"处理失败: {str(e)}"
            print(f"[CCXManager] {error_msg}")
            return (error_msg, "")

# 分身节点
class CCXManagerCopy:
    @classmethod
    def INPUT_TYPES(s):
        # 加载配置
        config_path = os.path.join(os.path.dirname(__file__), "config_copy.json")
        default_github_url = "https://github.com/zombieyang/sd-ppp.git"
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    default_github_url = config.get("github_repo_url", default_github_url)
        except Exception as e:
            print(f"[CCXManagerCopy] 加载配置失败: {str(e)}")

        return {
            "required": {
                "source_type": (["local_path", "url"], {"default": "url"}),
                "source_path": ("STRING", {"default": "https://gitee.com/zombieyang/sd-ppp/raw/main/static/sd-ppp_PS.ccx", "placeholder": "本地文件路径或URL"}),
                "github_repo_url": ("STRING", {"default": default_github_url, "placeholder": "GitHub仓库URL，留空禁用更新检测"}),
                "auto_run_on_restart": (["enable", "disable"], {"default": "enable"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("Status", "Generated_Path")
    FUNCTION = "process_ccx"
    CATEGORY = "Update of SD-PPP Plugin"
    TITLE = "Photoshop side automatic update SDPPP1.0"

    def __init__(self):
        # 使用独立配置文件
        self.manager = CCXManagerNode(config_filename="config_copy.json")
        # 初始化SDPPP路径管理器的配置
        self.config_sdppp_path = os.path.join(os.path.dirname(__file__), "config_sdppp_path.json")

    def _get_custom_nodes_path(self):
        """自动获取custom_nodes路径"""
        # 获取当前文件所在目录的父目录（即custom_nodes目录）
        current_dir = os.path.dirname(__file__)
        # 获取父目录，即custom_nodes目录
        custom_nodes_path = os.path.dirname(current_dir)
        
        print(f"[CCXManagerCopy] 自动识别的custom_nodes路径: {custom_nodes_path}")
        return custom_nodes_path

    def _save_sdppp_path_config(self, enable_update=True):
        """保存SDPPP路径配置"""
        try:
            config = {
                "enable_update": enable_update,
                "last_run_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "version": __version__
            }
            with open(self.config_sdppp_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            print(f"[CCXManagerCopy] SDPPP路径配置已保存到: {self.config_sdppp_path}")
        except Exception as e:
            print(f"[CCXManagerCopy] 保存SDPPP路径配置失败: {str(e)}")

    def process_ccx(self, source_type, source_path, github_repo_url, auto_run_on_restart):
        auto_run = auto_run_on_restart == "enable"
        # 更新GitHub仓库URL配置
        self.manager.config["github_repo_url"] = github_repo_url
        
        # 自动获取目标路径
        target_path = get_auto_target_path("sd-ppp_PS")
        if not target_path:
            return ("错误: 无法获取目标路径，请先使用Create SD-PPP installation directory节点设置基础路径", "")
        
        try:
            # 如果选择local_path，执行Comfyui side节点的功能
            generated_path = ""
            if source_type == "local_path":
                # 保存SDPPP路径配置
                self._save_sdppp_path_config(enable_update=True)
                
                # 自动获取custom_nodes路径
                custom_nodes_path = self._get_custom_nodes_path()
                
                # 验证custom_nodes_path是否存在
                if not os.path.exists(custom_nodes_path):
                    return (f"错误: 无法识别有效的custom_nodes目录: {custom_nodes_path}", "")
                
                # 生成对应的CCX文件路径
                generated_path = os.path.join(custom_nodes_path, "sd-ppp", "static", "sd-ppp_PS.ccx")
                
                # 输出运行信息
                print(f"[CCXManagerCopy] 运行信息:")
                print(f"[CCXManagerCopy] - 版本: SDPPP1.0")
                print(f"[CCXManagerCopy] - 自动识别的custom_nodes路径: {custom_nodes_path}")
                print(f"[CCXManagerCopy] - 生成的CCX路径: {generated_path}")
                print(f"[CCXManagerCopy] - 更新开关: {'开启' if auto_run else '关闭'}")
                print(f"[CCXManagerCopy] - 目标节点: CCXManagerCopy")
                
                # 自动设置source_path
                source_path = generated_path
                print(f"[CCXManagerCopy] SDPPP1.0节点自动填充路径: {source_path}")
            
            # 确保保存源路径和目标路径到配置中，防止下一次运行时丢失
            self.manager.config["source_path"] = source_path
            self.manager.config["target_path"] = target_path
            self.manager.save_config()
            
            if source_type == "url" and not source_path.startswith(("http://", "https://")):
                return ("错误: URL格式不正确", "")
            
            # 验证目标路径是否存在，如果不存在则尝试创建
            if not os.path.exists(target_path):
                try:
                    os.makedirs(target_path, exist_ok=True)
                    print(f"[CCXManagerCopy] 已创建目标目录: {target_path}")
                except Exception as mkdir_error:
                    return (f"错误: 无法创建目标目录: {str(mkdir_error)}", "")
            
            status = self.manager.run(source_path, target_path, auto_run)
            return (status, generated_path)
        except Exception as e:
            error_msg = f"处理失败: {str(e)}"
            print(f"[CCXManagerCopy] {error_msg}")
            return (error_msg, "")

# 创建安装目录节点
class CreateSDPPPInstallationDirectory:
    @classmethod
    def INPUT_TYPES(s):
        # 加载配置以获取保存的base_directory
        config_path = os.path.join(os.path.dirname(__file__), "config_dir.json")
        default_base_directory = ""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    default_base_directory = config.get("base_directory", "")
        except Exception as e:
            print(f"[CreateSDPPPInstallationDirectory] 加载配置失败: {str(e)}")

        return {
            "required": {
                "base_directory": ("STRING", {"default": default_base_directory, "placeholder": "基础目录路径，例如：C:/Program Files/Adobe/Adobe Photoshop 2025"}),
                "auto_run_on_restart": (["enable", "disable"], {"default": "enable"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("Status",)
    FUNCTION = "create_directories"
    CATEGORY = "Update of SD-PPP Plugin"
    TITLE = "Create SD-PPP installation directory"

    def __init__(self):
        self.config_path = os.path.join(os.path.dirname(__file__), "config_dir.json")
        self.config = self._load_config()

    def _load_config(self):
        """加载配置文件，如果不存在则创建默认配置"""
        default_config = {
            "base_directory": "",
            "auto_run_on_restart": True,
            "last_run_time": "",
            "version": __version__
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
            print(f"[CreateSDPPPInstallationDirectory] 加载配置失败: {str(e)}")
            return default_config

    def _save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[CreateSDPPPInstallationDirectory] 保存配置失败: {str(e)}")

    def create_directories(self, base_directory, auto_run_on_restart):
        try:
            # 确保路径以\Plug-ins结尾
            normalized_base_directory = base_directory.rstrip('\\/')
            if not normalized_base_directory.lower().endswith('\\plug-ins') and not normalized_base_directory.lower().endswith('/plug-ins'):
                normalized_base_directory += '\\Plug-ins'
            
            # 更新配置
            self.config["base_directory"] = normalized_base_directory
            self.config["auto_run_on_restart"] = auto_run_on_restart == "enable"
            self.config["last_run_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_config()

            # 验证基础目录是否存在
            if not normalized_base_directory:
                return ("错误: 基础目录路径未设置",)
            
            if not os.path.exists(normalized_base_directory):
                return (f"错误: 基础目录不存在: {normalized_base_directory}",)
            
            # 创建两个目标文件夹
            folders_to_create = ["sd-ppp_PS", "sd-ppp2_PS"]
            created_folders = []
            
            for folder_name in folders_to_create:
                folder_path = os.path.join(normalized_base_directory, folder_name)
                os.makedirs(folder_path, exist_ok=True)
                created_folders.append(folder_path)
                print(f"[CreateSDPPPInstallationDirectory] 已创建文件夹: {folder_path}")
            
            status_msg = f"成功: 已在 {normalized_base_directory} 下创建文件夹: {', '.join(folders_to_create)}"
            print(f"[CreateSDPPPInstallationDirectory] {status_msg}")
            return (status_msg,)
        except Exception as e:
            error_msg = f"创建文件夹失败: {str(e)}"
            print(f"[CreateSDPPPInstallationDirectory] {error_msg}")
            return (error_msg,)
    
    def auto_run(self):
        """启动时自动运行目录创建功能"""
        auto_run_enabled = self.config.get("auto_run_on_restart", True)
        base_directory = self.config.get("base_directory", "")
        
        if auto_run_enabled and base_directory:
            print(f"[CreateSDPPPInstallationDirectory] 检测到自动运行配置，正在创建目录...")
            # 直接调用创建目录的逻辑
            try:
                if os.path.exists(base_directory):
                    # 创建两个目标文件夹
                    folders_to_create = ["sd-ppp_PS", "sd-ppp2_PS"]
                    for folder_name in folders_to_create:
                        folder_path = os.path.join(base_directory, folder_name)
                        if os.path.exists(folder_path):
                            print(f"[CreateSDPPPInstallationDirectory] {folder_name}文件夹已存在")
                        else:
                            os.makedirs(folder_path, exist_ok=True)
                            print(f"[CreateSDPPPInstallationDirectory] 自动运行: 已创建文件夹: {folder_path}")
                    print(f"[CreateSDPPPInstallationDirectory] 自动运行: 目录创建成功")
                else:
                    print(f"[CreateSDPPPInstallationDirectory] 自动运行失败: 基础目录不存在: {base_directory}")
            except Exception as e:
                print(f"[CreateSDPPPInstallationDirectory] 自动运行失败: {str(e)}")
        else:
            print(f"[CreateSDPPPInstallationDirectory] 自动运行已禁用或基础目录未设置")

# 已将Comfyui side automatic update SD-PPP节点的功能合并到SDPPP1.0和SDPPP2.0节点中

# 修改现有节点以支持自动填充路径
# 修改CCXManager（SDPPP2.0）的process_ccx方法
original_process_ccx = CCXManager.process_ccx
def modified_process_ccx_20(self, source_type, source_path, github_repo_url, auto_run_on_restart):
    # 如果选择local_path，自动获取正确的ccx文件路径
    if source_type == "local_path":
        try:
            # 自动获取custom_nodes路径（当前文件所在目录的父目录）
            current_dir = os.path.dirname(__file__)
            custom_nodes_path = os.path.dirname(current_dir)
            source_path = os.path.join(custom_nodes_path, "sd-ppp", "static", "sd-ppp2_PS.ccx")
            print(f"[CCXManager] SDPPP2.0节点自动填充路径: {source_path}")
        except Exception as e:
            print(f"[CCXManager] 自动获取路径失败: {str(e)}")
    
    # 调用原始方法
    return original_process_ccx(self, source_type, source_path, github_repo_url, auto_run_on_restart)

# 修改CCXManagerCopy（SDPPP1.0）的process_ccx方法
original_process_ccx_copy = CCXManagerCopy.process_ccx
def modified_process_ccx_10(self, source_type, source_path, github_repo_url, auto_run_on_restart):
    # 如果选择local_path且source_path为空，自动获取路径
    if source_type == "local_path" and not source_path:
        try:
            # 自动获取custom_nodes路径（当前文件所在目录的父目录）
            current_dir = os.path.dirname(__file__)
            custom_nodes_path = os.path.dirname(current_dir)
            source_path = os.path.join(custom_nodes_path, "sd-ppp", "static", "sd-ppp_PS.ccx")
            print(f"[CCXManagerCopy] 自动识别并填充local_path: {source_path}")
        except Exception as e:
            print(f"[CCXManagerCopy] 自动获取路径失败: {str(e)}")
    
    # 调用原始方法
    return original_process_ccx_copy(self, source_type, source_path, github_repo_url, auto_run_on_restart)

# 应用修改
CCXManager.process_ccx = modified_process_ccx_20
CCXManagerCopy.process_ccx = modified_process_ccx_10

# 已移除工作流状态跟踪，因为Comfyui side节点功能已合并到SDPPP1.0和SDPPP2.0节点中

# 已移除节点状态跟踪相关的修改

# 已移除依赖检查相关的修改，因为功能已合并

# 节点注册
NODE_CLASS_MAPPINGS = {
    "CCXManager": CCXManager,
    "CCXManagerCopy": CCXManagerCopy,
    "CreateSDPPPInstallationDirectory": CreateSDPPPInstallationDirectory
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CCXManager": "Photoshop side automatic update SDPPP2.0",
    "CCXManagerCopy": "Photoshop side automatic update SDPPP1.0",
    "CreateSDPPPInstallationDirectory": "Create SD-PPP installation directory"
}

# 程序启动时自动检查并运行
print(f"[CCXManager] Photoshop侧自动更新SD-PPP节点已加载 (版本: {__version__})")
# 首先运行目录创建节点（优先级最高）
dir_creator = CreateSDPPPInstallationDirectory()
dir_creator.auto_run()

# 然后运行其他节点的自动检查
# 主节点（SDPPP2.0）自动运行检查
manager = CCXManagerNode()
manager.auto_run()

# SDPPP1.0自动运行检查（使用独立配置文件）
manager_copy = CCXManagerNode(config_filename="config_copy.json")
manager_copy.auto_run()
# 克隆节点自动运行检查
manager_copy = CCXManagerNode(config_filename="config_copy.json")
manager_copy.auto_run()

