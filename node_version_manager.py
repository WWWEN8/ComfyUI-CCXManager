import os
import sys
import json
import subprocess
import tempfile
import shutil
from datetime import datetime

class NodeVersionController:
    """节点版本控制器，用于管理节点的版本切换功能"""
    def __init__(self):
        self.comfyui_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.custom_nodes_path = os.path.join(self.comfyui_path, "custom_nodes")
        
    def is_git_installed(self):
        """检查Git是否安装"""
        try:
            subprocess.run(["git", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def get_node_commit_history(self, node_name, max_count=None):
        """获取节点的提交历史"""
        try:
            node_path = os.path.join(self.custom_nodes_path, node_name)
            
            # 检查节点目录是否存在
            if not os.path.exists(node_path):
                return False, f"Node directory not found: {node_name}"
            
            # 检查是否是Git仓库
            if not os.path.exists(os.path.join(node_path, ".git")):
                return False, f"Node is not a Git repository: {node_name}"
            
            # 获取当前分支
            branch_result = subprocess.run(
                ["git", "-C", node_path, "rev-parse", "--abbrev-ref", "HEAD"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "(detached HEAD)"
            
            # 获取提交历史
            log_cmd = ["git", "-C", node_path, "log", "--pretty=format:%h|%an|%ad|%s", "--date=short"]
            if max_count:
                log_cmd.extend(["-n", str(max_count)])
            
            result = subprocess.run(
                log_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if result.returncode != 0:
                return False, f"Failed to get commit history: {result.stderr}"

            # 解析提交历史
            commits = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("|", 3)
                    if len(parts) >= 4:
                        commits.append({
                            "hash": parts[0],
                            "author": parts[1],
                            "date": parts[2],
                            "message": parts[3]
                        })

            return True, {"branch": current_branch, "commits": commits}
        except Exception as e:
            return False, f"Error getting commit history: {str(e)}"

    def switch_node_version(self, node_name, version_offset, auto_add_to_ignore=True):
        """切换节点版本
        
        Args:
            node_name: Node name
            version_offset: Version offset, 1 means latest version, negative numbers mean going back from latest version
        """
        try:
            node_path = os.path.join(self.custom_nodes_path, node_name)
            
            # 检查节点目录是否存在
            if not os.path.exists(node_path):
                return False, f"Node directory not found: {node_name}"
            
            # 检查是否是Git仓库
            if not os.path.exists(os.path.join(node_path, ".git")):
                return False, f"Node is not a Git repository: {node_name}"
            
            # 获取当前分支
            branch_result = subprocess.run(
                ["git", "-C", node_path, "rev-parse", "--abbrev-ref", "HEAD"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "(detached HEAD)"
            
            # 如果当前是游离状态，使用默认分支
            if current_branch == "HEAD" or current_branch == "(detached HEAD)":
                # 尝试获取默认分支
                default_branch_result = subprocess.run(
                    ["git", "-C", node_path, "symbolic-ref", "refs/remotes/origin/HEAD"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if default_branch_result.returncode == 0:
                    # 从输出如"refs/remotes/origin/main"中提取"main"
                    current_branch = default_branch_result.stdout.strip().split("/")[-1]
                    # 切换到默认分支
                    subprocess.run(["git", "-C", node_path, "checkout", current_branch], check=False)
                else:
                    # 如果无法获取默认分支，创建一个临时分支
                    current_branch = f"temp_branch_{int(datetime.now().timestamp())}"
                    subprocess.run(["git", "-C", node_path, "checkout", "-b", current_branch], check=False)
            
            # 检查是否有未提交的更改
            status_result = subprocess.run(
                ["git", "-C", node_path, "status", "--porcelain"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            has_stashed_changes = False
            
            # 如果有未提交的更改，暂存它们
            if status_result.stdout.strip():
                subprocess.run(["git", "-C", node_path, "stash", "push", "-m", "Auto-stash before version switch"], check=False)
                has_stashed_changes = True
            
            # 新的版本切换逻辑：
            # 1表示最新版本，负数表示从最新版本开始后退相应数量的版本
            if version_offset != 1 and version_offset >= 0:
                return False, "Error: Version offset can only be 1 (latest) or negative numbers (e.g., -2, -3)"
            
            # 无论选择什么版本，都先拉取最新代码以确保有完整的提交历史
            print(f"[NodeVersionController] Pulling latest code for node {node_name}...")
            fetch_result = subprocess.run(
                ["git", "-C", node_path, "fetch"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if fetch_result.returncode != 0:
                print(f"[NodeVersionController] Failed to pull code: {fetch_result.stderr}")
            
            # 尝试合并最新代码
            pull_result = subprocess.run(
                ["git", "-C", node_path, "pull"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if pull_result.returncode != 0:
                print(f"[NodeVersionController] Failed to merge latest code, using local latest commit: {pull_result.stderr}")
            
            # 确定目标提交
            if version_offset == 1:
                target_commit = "HEAD"
                print(f"[NodeVersionController] Switching node {node_name} to latest version...")
            else:  # 负数偏移量
                target_commit = f"HEAD~{abs(version_offset)}"
                print(f"[NodeVersionController] Going back {abs(version_offset)} versions from latest")
            
            # 创建临时分支指向目标提交
            temp_branch = f"temp_version_switch_{int(datetime.now().timestamp())}"
            checkout_result = subprocess.run(
                ["git", "-C", node_path, "checkout", "-b", temp_branch, target_commit],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if checkout_result.returncode != 0:
                # 如果切换失败，恢复stash（如果有）
                if has_stashed_changes:
                    subprocess.run(["git", "-C", node_path, "stash", "pop"], check=False)
                return False, f"Failed to switch to target commit: {checkout_result.stderr}"
            
            # 切换回原来的分支
            subprocess.run(["git", "-C", node_path, "checkout", current_branch], check=False)
            
            # 强制将原来的分支重置到临时分支的位置
            reset_result = subprocess.run(
                ["git", "-C", node_path, "reset", "--hard", temp_branch],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 删除临时分支
            subprocess.run(["git", "-C", node_path, "branch", "-D", temp_branch], check=False)
            
            if reset_result.returncode != 0:
                # 如果重置失败，恢复stash（如果有）
                if has_stashed_changes:
                    subprocess.run(["git", "-C", node_path, "stash", "pop"], check=False)
                return False, f"Failed to reset branch: {reset_result.stderr}"
            
            # 操作成功后输出日志
            if version_offset == 1:
                print(f"[NodeVersionController] Successfully switched node {node_name} to latest version")
            else:  # 负数偏移量
                print(f"[NodeVersionController] Successfully went back {abs(version_offset)} versions from latest")

            # 获取切换后的提交信息
            new_commit_result = subprocess.run(
                ["git", "-C", node_path, "log", "-1", "--pretty=format:%h|%an|%ad|%s", "--date=short"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if new_commit_result.returncode != 0:
                return False, "Failed to get new commit information"

            new_commit_info = new_commit_result.stdout.strip().split("|", 3)
            if len(new_commit_info) >= 4:
                new_commit_hash = new_commit_info[0]
                new_commit_message = new_commit_info[3]
                new_commit_date = new_commit_info[2]
            else:
                return False, "Failed to parse new commit information"

            # 根据版本偏移量构建更明确的消息
            if version_offset == 1:
                message = f"Successfully switched node {node_name} to latest version: {new_commit_hash}\nCommit message: {new_commit_message}\nCommit date: {new_commit_date}\nBranch: {current_branch}\n"
            else:  # 负数偏移量
                message = f"Successfully went back {abs(version_offset)} versions to: {new_commit_hash}\nCommit message: {new_commit_message}\nCommit date: {new_commit_date}\nBranch: {current_branch}\n"
            
            if has_stashed_changes:
                message += "Note: Uncommitted changes were stashed"

            return True, message
        except Exception as e:
            return False, f"Error switching version: {str(e)}"

# NodeVersionManager class definition - English version
class NodeVersionManager:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "node_name": ("STRING", {"default": "", "multiline": False, "placeholder": "Enter node name to switch version"}),
                "version_offset": ("INT", {"default": 1, "min": -99999, "max": 1, "step": 1, "placeholder": "1=Latest version, -2,-3 etc=Go back from latest"}),
                "show_history": ("BOOLEAN", {"default": False, "label_on": "Show History", "label_off": "Don't Show History"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("Result Message",)
    FUNCTION = "process"
    CATEGORY = "Update of SD-PPP Plugin"

    def process(self, node_name, version_offset, show_history):
        controller = NodeVersionController()
        status_message = ""

        if not node_name.strip():
            return ("Error: Please enter node name",)

        # 检查节点是否存在
        node_path = os.path.join(controller.custom_nodes_path, node_name)
        if not os.path.exists(node_path) or not os.path.isdir(node_path):
            return (f"Error: Node {node_name} not found",)

        # 如果请求显示历史
        if show_history:
            success, result = controller.get_node_commit_history(node_name)
            if success:
                status_message += f"Commit history for node {node_name} (branch: {result['branch']}):\n"
                for i, commit in enumerate(result['commits']):
                    status_message += f"[{i}] {commit['hash'][:7]} | {commit['date']} | {commit['message'][:50]}...\n"
            else:
                return (f"Failed to get history: {result}",)
        else:
            # 执行版本切换
            if version_offset == 0:
                return ("Error: Version offset cannot be 0",)
            
            success, message = controller.switch_node_version(node_name, version_offset)
            if success:
                status_message += message
            else:
                return (f"Failed to switch version: {message}",)

        return (status_message,)

# 节点注册映射
NODE_CLASS_MAPPINGS = {
    "NodeVersionManager": NodeVersionManager
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NodeVersionManager": "Node Version Switcher"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']