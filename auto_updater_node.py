import os
import sys
import json
import subprocess
import requests
import shutil
import tempfile
from datetime import datetime
from urllib.parse import urlparse
import threading
from concurrent.futures import ThreadPoolExecutor

__version__ = "2.0"

class GitHubRepoUpdater:
    """GitHub仓库更新器，用于检查和更新指定的GitHub仓库"""
    def __init__(self):
        self.comfyui_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.custom_nodes_path = os.path.join(self.comfyui_path, "custom_nodes")
        self.updater_config_path = os.path.join(os.path.dirname(__file__), "updater_config.json")
        self.config = self.load_config()
        self.repo_cache = {}
        self.updatable_repos = []
        self.updated_count = 0

    def load_config(self):
        """加载更新器配置文件"""
        default_config = {
            "repos": [],  # 存储要监控的仓库信息
            "auto_update_on_start": True,
            "last_check_time": "",
            "check_interval_days": 1,
            "max_workers": 5
        }
        try:
            if os.path.exists(self.updater_config_path):
                with open(self.updater_config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                with open(self.updater_config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4, ensure_ascii=False)
                return default_config
        except Exception as e:
            print(f"[CCXManager Updater] 加载配置失败: {str(e)}")
            return default_config

    def save_config(self):
        """保存更新器配置文件"""
        try:
            with open(self.updater_config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[CCXManager Updater] 保存配置失败: {str(e)}")

    def is_git_installed(self):
        """检查Git是否安装"""
        try:
            subprocess.run(["git", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def add_repo(self, repo_url, node_name=None, branch="main", auto_update=True):
        """添加要监控的仓库"""
        if not repo_url:
            return False, "仓库URL不能为空"
            
        # 如果没有提供节点名称，从URL中提取
        if not node_name:
            parsed_url = urlparse(repo_url)
            path_parts = parsed_url.path.strip('/').split('/')
            if len(path_parts) >= 2:
                node_name = path_parts[1].replace('.git', '')
            else:
                node_name = "unknown_repo"

        # 获取当前SHA
        current_sha = ""
        try:
            current_sha = self.get_remote_sha(repo_url, branch)
        except Exception as e:
            print(f"[CCXManager Updater] 获取SHA失败: {str(e)}")

        # 清空现有仓库列表，只保留当前设置的仓库
        self.config["repos"] = [{
            "repo_url": repo_url,
            "node_name": node_name,
            "branch": branch,
            "auto_update": auto_update,
            "last_commit_sha": current_sha,
            "last_update_time": ""
        }]
        
        self.save_config()
        return True, f"成功添加仓库监控: {node_name}，已自动清除旧仓库配置"

    def get_remote_sha(self, repo_url, branch="main"):
        """获取远程仓库的最新SHA"""
        # 检查缓存
        cache_key = f"{repo_url}:{branch}"
        if cache_key in self.repo_cache:
            cached_sha, cached_time = self.repo_cache[cache_key]
            # 缓存5分钟
            if (datetime.now() - cached_time).total_seconds() < 300:
                return cached_sha

        # 尝试使用git命令直接获取（参考Comfy-NodeUpdater的方式）
        if self.is_git_installed():
            try:
                result = subprocess.run(
                    ["git", "ls-remote", repo_url, branch],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if result.returncode == 0 and result.stdout:
                    sha = result.stdout.split()[0]
                    self.repo_cache[cache_key] = (sha, datetime.now())
                    return sha
            except Exception as e:
                # 不打印详细错误信息
                pass
                
        # 尝试使用GitHub API（备选方案）
        try:
            parsed_url = urlparse(repo_url)
            if parsed_url.netloc == "github.com":
                path_parts = parsed_url.path.strip('/').split('/')
                if len(path_parts) >= 2:
                    owner, repo = path_parts[:2]
                    # 移除仓库名称中的.git后缀
                    if repo.endswith('.git'):
                        repo = repo[:-4]
                    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"
                    
                    # 添加错误处理和超时设置
                    try:
                        response = requests.get(api_url, timeout=10)
                        if response.status_code == 200:
                            sha = response.json().get("sha", "")
                            if sha:
                                self.repo_cache[cache_key] = (sha, datetime.now())
                                return sha
                    except requests.RequestException:
                        # 捕获网络相关异常，不打印详细信息
                        pass
        except Exception as e:
            # 不打印详细错误信息
            pass
            
        # 所有方法都失败，抛出异常
        raise Exception("无法获取远程仓库的SHA")

    def check_repo_for_update(self, repo_info):
        """检查单个仓库是否有更新"""
        node_name = repo_info["node_name"]
        
        if not repo_info["auto_update"]:
            return node_name, False, "自动更新已禁用"

        # 检查本地仓库是否存在
        node_path = os.path.join(self.custom_nodes_path, node_name)
        git_path = os.path.join(node_path, ".git")
        
        if not os.path.exists(git_path):
            # 本地没有仓库，视为需要更新
            return node_name, True, "本地仓库不存在"
        
        try:
            # 尝试使用本地git命令检查更新
            try:
                # 执行git fetch，移除重复的打印信息
                fetch_result = subprocess.run(
                    ["git", "-C", node_path, "fetch"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if fetch_result.returncode == 0:
                    # 检查本地与远程的差异
                    status_result = subprocess.run(
                        ["git", "-C", node_path, "status", "-uno"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    has_updates = "Your branch is behind" in status_result.stdout
                    return node_name, has_updates, "本地git检查成功"
                else:
                    # git fetch失败，记录错误但不打印到控制台
                    error_msg = f"git fetch失败"
                    return node_name, False, error_msg  # 立即返回错误，不继续执行
            except Exception as e:
                # 本地git操作异常，不打印详细错误到控制台
                error_msg = f"本地git操作异常"
                return node_name, False, error_msg  # 立即返回错误，不继续执行
                
            # 注意：以下代码在git操作失败时不会执行，因为上面已经返回了
            current_sha = self.get_remote_sha(repo_info["repo_url"], repo_info["branch"])
            has_update = current_sha != repo_info["last_commit_sha"] or repo_info["last_commit_sha"] == ""
            return node_name, has_update, current_sha
        except Exception as e:
            # 检查更新异常，不打印详细错误到控制台
            return node_name, False, "检查更新异常"

    def update_repo(self, repo_info, force_override=False):
        """更新单个仓库（参考Comfy-NodeUpdater的实现）"""
        node_name = repo_info["node_name"]
        node_path = os.path.join(self.custom_nodes_path, node_name)
        repo_url = repo_info["repo_url"]
        branch = repo_info["branch"]

        try:
            # 检查目录是否存在
            if not os.path.exists(node_path):
                # 目录不存在，执行克隆
                print(f"[CCXManager Updater] 开始克隆仓库: {node_name}")
                result = subprocess.run(
                    ["git", "clone", "-b", branch, repo_url, node_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if result.returncode != 0:
                    return False, f"克隆失败: {result.stderr}"
            else:
                # 目录存在，执行pull（参考Comfy-NodeUpdater的错误处理）
                print(f"[CCXManager Updater] 开始更新仓库: {node_name}")
                
                # 先尝试直接pull
                result = subprocess.run(
                    ["git", "-C", node_path, "pull"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if result.returncode != 0:
                    # 检查是否是因为本地更改冲突导致的失败
                    if "Your local changes to the following files would be overwritten by merge" in result.stderr or force_override:
                        print(f"[CCXManager Updater] 检测到{node_name}有未提交的更改，正在自动放弃本地更改...")
                        
                        # 尝试常规的checkout
                        checkout_result = subprocess.run(
                            ["git", "-C", node_path, "checkout", "--", "."],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        
                        if checkout_result.returncode != 0 or force_override:
                            # 如果常规checkout失败或用户选择强制覆盖，使用更强制的方法
                            print(f"[CCXManager Updater] 尝试强制清理{node_name}的未跟踪文件...")
                            # 清理未跟踪的文件和目录
                            clean_result = subprocess.run(
                                ["git", "-C", node_path, "clean", "-fd"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True
                            )
                            if clean_result.returncode != 0:
                                return False, f"强制清理失败: {clean_result.stderr}"
                            
                            # 再次尝试checkout
                            checkout_result = subprocess.run(
                                ["git", "-C", node_path, "checkout", "--", "."],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True
                            )
                        
                        if checkout_result.returncode == 0:
                            print(f"[CCXManager Updater] {node_name}本地更改已放弃，正在重新尝试更新...")
                            # 再次尝试git pull
                            retry_result = subprocess.run(
                                ["git", "-C", node_path, "pull"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True
                            )
                            if retry_result.returncode == 0:
                                # 更新成功
                                pass
                            else:
                                return False, f"放弃更改后更新仍失败: {retry_result.stderr}"
                        else:
                            return False, f"放弃本地更改失败: {checkout_result.stderr}"
                    else:
                        return False, f"更新失败: {result.stderr}"

            # 更新SHA和时间
            current_sha = self.get_remote_sha(repo_url, branch)
            for repo in self.config["repos"]:
                if repo["node_name"] == node_name:
                    repo["last_commit_sha"] = current_sha
                    repo["last_update_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    break
            self.save_config()

            return True, "更新成功"
        except Exception as e:
            return False, f"更新异常: {str(e)}"

    def check_all_repos(self):
        """检查所有监控的仓库是否有更新（使用线程池并发处理）"""
        if not self.is_git_installed():
            print("[CCXManager Updater] 未安装Git，请先安装Git")
            return [], "未安装Git"

        if not self.config["repos"]:
            return [], "没有监控的仓库"

        self.updatable_repos = []
        status_message = "检查仓库更新结果:\n"
        has_any_update = False
        has_any_disabled = False

        # 使用线程池并发检查
        with ThreadPoolExecutor(max_workers=self.config.get("max_workers", 5)) as executor:
            results = list(executor.map(self.check_repo_for_update, self.config["repos"]))

        for node_name, has_update, result in results:
            if has_update:
                # 查找对应的repo_info
                repo_info = next((r for r in self.config["repos"] if r["node_name"] == node_name), None)
                if repo_info:
                    self.updatable_repos.append(repo_info)
                    status_message += f"✅ {node_name}: 发现更新\n"
                    has_any_update = True
            else:
                if isinstance(result, str):
                    if result != "自动更新已禁用" and "成功" not in result:
                        # 不显示详细的错误信息
                        status_message += f"❌ {node_name}: {result}\n"
                    elif result != "自动更新已禁用":
                        status_message += f"✅ {node_name}: 已是最新版本\n"
                    else:
                        status_message += f"🔄 {node_name}: 自动更新已禁用\n"
                        has_any_disabled = True
                else:
                    status_message += f"✅ {node_name}: 已是最新版本\n"

        # 只输出一次状态信息，避免重复
        if has_any_update:
            print("[CCXManager Updater] 发现有更新，正在更新中")
        elif has_any_disabled:
            print("[CCXManager Updater] 已经忽略更新")
        else:
            print("[CCXManager Updater] 没发现更新")

        self.config["last_check_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_config()
        
        return self.updatable_repos, status_message

    def update_all_repos(self, force_override=False):
        """更新所有有更新的仓库（使用线程池并发处理）"""
        if not self.updatable_repos:
            # 如果没有预先检查，先检查
            self.check_all_repos()

        if not self.updatable_repos:
            print("[CCXManager Updater] 没有需要更新的仓库")
            return 0, "没有需要更新的仓库"

        self.updated_count = 0
        status_message = "更新结果:\n"
        update_results = []

        # 使用线程池并发更新，并传递force_override参数（参考Comfy-NodeUpdater）
        with ThreadPoolExecutor(max_workers=self.config.get("max_workers", 5)) as executor:
            results = list(executor.map(lambda repo: (repo, self.update_repo(repo, force_override)), self.updatable_repos))

        for repo_info, (success, message) in results:
            node_name = repo_info["node_name"]
            if success:
                self.updated_count += 1
                result_msg = f"✅ {node_name}: {message}\n"
                print("[CCXManager Updater] SDPPP节点更新成功")
            else:
                result_msg = f"❌ {node_name}: {message}\n"
                print(f"[CCXManager Updater] {result_msg.strip()}")  # 打印每个节点的更新结果到控制台
            status_message += result_msg
            update_results.append(result_msg.strip())

        return self.updated_count, status_message

    def run_auto_update(self, force_override=False, force_update=False):
        """执行自动更新"""
        if not self.config.get("auto_update_on_start", True):
            print("[CCXManager Updater] Comfyui侧自动更新SDPPP节点已禁用")
            return 0, "自动更新已禁用"

        # 添加时间间隔检查，但仅在非强制更新模式下
        if not force_update and self.config.get("last_check_time") and self.config.get("check_interval_days", 1) > 0:
            try:
                last_check = datetime.strptime(self.config["last_check_time"], "%Y-%m-%d %H:%M:%S")
                current_time = datetime.now()
                days_since_last_check = (current_time - last_check).days
                
                # 检查是否是未来时间
                if last_check > current_time:
                    print(f"[CCXManager Updater] 检测到未来的检查时间，重置并执行检查")
                    # 重置为当前时间
                    self.config["last_check_time"] = current_time.strftime("%Y-%m-%d %H:%M:%S")
                    self.save_config()
                elif days_since_last_check < self.config["check_interval_days"]:
                    print(f"[CCXManager Updater] 距离上次检查不足{self.config['check_interval_days']}天，跳过自动更新")
                    return 0, f"距离上次检查不足{self.config['check_interval_days']}天，跳过自动更新"
            except Exception as e:
                print(f"[CCXManager Updater] 时间检查出错: {str(e)}")
                # 如果时间解析失败，继续执行更新检查

        print("[CCXManager Updater] 正在SDPPP节点检查更新...")
        
        # 确保只保留当前设置的仓库（如果有的话）
        if len(self.config["repos"]) > 1:
            print("[CCXManager Updater] 检测到多个仓库配置，仅保留当前设置的仓库")
            # 保留最后一个仓库配置
            self.config["repos"] = [self.config["repos"][-1]]
            self.save_config()
            
        self.check_all_repos()
        if self.updatable_repos:
            count, message = self.update_all_repos(force_override)
            return count, message
        else:
            return 0, "没有需要更新的仓库"

class CCXRepoUpdaterNode:
    """CCX仓库更新器节点，简化版本"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "repo_url": ("STRING", {"default": "", "multiline": False, "placeholder": "GitHub仓库URL，如：https://github.com/user/repo.git"}),
                "auto_update": ("BOOLEAN", {"default": True}),
                "force_override": ("BOOLEAN", {"default": False})
            },
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "process"
    CATEGORY = "SD-PPP插件更新"

    def process(self, repo_url, auto_update, force_override):
        updater = GitHubRepoUpdater()
        status_message = ""
        
        if not repo_url:
            status_message = "错误：仓库URL不能为空"
            return (status_message,)
        
        # 从URL提取节点名称
        parsed_url = urlparse(repo_url)
        path_parts = parsed_url.path.strip('/').split('/')
        if len(path_parts) >= 2:
            node_name = path_parts[1].replace('.git', '')
        else:
            node_name = "unknown_repo"
        
        # 无论仓库是否存在，都调用add_repo方法以确保旧仓库被删除
        success, message = updater.add_repo(repo_url, node_name, "main", auto_update)
        if not success:
            status_message = message
            return (status_message,)
        
        # 先检测更新状态
        print(f"[CCXManager Updater] 开始检查仓库 {node_name} 的更新状态...")
        repo_info = next((repo for repo in updater.config["repos"] if repo["node_name"] == node_name), None)
        if repo_info:
            node_name_result, has_update, result = updater.check_repo_for_update(repo_info)
            
            if has_update and auto_update:
                # 有更新且开启自动更新，执行更新
                print(f"[CCXManager Updater] 发现仓库 {node_name} 的更新，开始更新...")
                success, update_message = updater.update_repo(repo_info, force_override)
                if success:
                    status_message = f"✅ {node_name}: 更新成功 [自动更新: 开启]"
                    print(f"[CCXManager Updater] {status_message}")
                else:
                    status_message = f"❌ {node_name}: 更新失败 - {update_message} [自动更新: 开启]"
                    print(f"[CCXManager Updater] {status_message}")
            elif has_update:
                # 有更新但未开启自动更新
                status_message = f"ℹ️ {node_name}: 发现更新，但自动更新已禁用"
                print(f"[CCXManager Updater] {status_message}")
            elif isinstance(result, str) and result != "自动更新已禁用":
                # 检查失败 - 直接使用返回的具体错误信息并添加自动更新状态
                update_status = "[自动更新: 开启]" if auto_update else "[自动更新: 禁用]"
                if result.startswith("本地git检查成功"):
                    status_message = f"✅ {node_name}: {result} {update_status}"
                else:
                    status_message = f"❌ {node_name}: {result} {update_status}"
                print(f"[CCXManager Updater] {status_message}")
            else:
                # 已是最新版本并添加自动更新状态
                update_status = "[自动更新: 开启]" if auto_update else "[自动更新: 禁用]"
                status_message = f"✅ {node_name}: 已是最新版本 {update_status}"
                print(f"[CCXManager Updater] {status_message}")
        else:
            status_message = "错误：无法找到仓库信息"
        
        return (status_message,)

# 全局自动更新函数
def auto_check_for_repo_updates():
    """ComfyUI启动时自动检查仓库更新"""
    try:
        updater = GitHubRepoUpdater()
        # 获取当前自动更新设置状态
        auto_update_status = updater.config.get("auto_update_on_start", True)
        # 在控制台显示自动更新状态
        print(f"[CCXManager Updater] Comfyui侧自动更新SDPPP节点已{'启动' if auto_update_status else '禁用'}")
        
        if auto_update_status:
            # 自动更新时不使用强制覆盖，但使用强制更新模式（忽略时间间隔）
            updater.run_auto_update(False, True)
        else:
            print("[CCXManager Updater] 由于自动更新功能已禁用，跳过更新检查")
    except Exception as e:
        print(f"[CCXManager Updater] 自动更新失败: {str(e)}")

# 节点注册映射
NODE_CLASS_MAPPINGS = {
    "CCXRepoUpdaterNode": CCXRepoUpdaterNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CCXRepoUpdaterNode": "Comfyui side automatic update SDPPP"
}