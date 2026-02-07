from server import PromptServer
import os
import json
import threading
import time
import uuid
import asyncio
import random
import re
from aiohttp import web
import execution
import nodes

CATEGORY_TYPE = "Update of SD-PPP Plugin"

# ============ 后台执行辅助函数 ============

def recursive_add_nodes(node_id, old_output, new_output):
    """从输出节点递归收集所有依赖节点（与前端 queueManager.recursiveAddNodes 逻辑完全一致）"""
    current_id = str(node_id)
    current_node = old_output.get(current_id)
    
    if not current_node:
        print(f"[CCXGroupExecutor] 节点 {current_id} 在输出中不存在")
        return new_output
    
    if new_output.get(current_id) is None:
        print(f"[CCXGroupExecutor] 添加节点: {current_id} (类型: {current_node.get('class_type', 'unknown')})")
        new_output[current_id] = current_node
        inputs = current_node.get("inputs", {})
        
        for input_name, input_value in inputs.items():
            if isinstance(input_value, list):
                # 标准输入格式: [source_node_id, output_index]
                source_node_id = input_value[0]
                if source_node_id is not None and source_node_id != "":
                    print(f"[CCXGroupExecutor] 节点 {current_id} 的输入 {input_name} 来自节点 {source_node_id}")
                    recursive_add_nodes(source_node_id, old_output, new_output)
                else:
                    print(f"[CCXGroupExecutor] 节点 {current_id} 的输入 {input_name} 没有源节点")
            elif isinstance(input_value, dict) and "link_id" in input_value:
                # 某些节点可能使用link_id格式
                link_id = input_value["link_id"]
                if link_id:
                    print(f"[CCXGroupExecutor] 节点 {current_id} 的输入 {input_name} 来自link_id {link_id}")
                    recursive_add_nodes(link_id, old_output, new_output)
    
    return new_output

def filter_prompt_for_nodes(full_prompt, output_node_ids):
    """从完整的 API prompt 中筛选出指定输出节点及其依赖"""
    filtered_prompt = {}
    
    for node_id in output_node_ids:
        # 确保node_id是字符串
        node_id_str = str(node_id)
        
        # 首先检查该节点是否存在
        if node_id_str not in full_prompt:
            print(f"[CCXGroupExecutor] 警告：输出节点 {node_id_str} 不在完整prompt中")
            continue
            
        print(f"[CCXGroupExecutor] 开始筛选节点，输出节点: {node_id_str}")
        
        # 递归收集所有依赖节点
        recursive_add_nodes(node_id_str, full_prompt, filtered_prompt)
        
    print(f"[CCXGroupExecutor] 筛选完成，共收集 {len(filtered_prompt)} 个节点")
    return filtered_prompt

class GroupExecutorBackend:
    """后台执行管理器"""
    
    def __init__(self):
        self.running_tasks = {}
        self.task_lock = threading.Lock()
        self.interrupted_prompts = set()  # 记录被中断的 prompt_id
        self._setup_interrupt_handler()
    
    def _setup_interrupt_handler(self):
        """设置中断处理器，监听 execution_interrupted 消息"""
        try:
            server = PromptServer.instance
            backend_instance = self
            
            # 保存原始的 send_sync 方法
            original_send_sync = server.send_sync
            
            def patched_send_sync(event, data, sid=None):
                try:
                    # 调用原始方法，添加错误处理
                    original_send_sync(event, data, sid)
                    
                    # 监听 execution_interrupted 事件
                    if event == "execution_interrupted":
                        prompt_id = data.get("prompt_id")
                        if prompt_id:
                            backend_instance.interrupted_prompts.add(prompt_id)
                            # 取消所有后台任务
                            backend_instance._cancel_all_on_interrupt()
                except Exception as e:
                    # 忽略所有WebSocket和连接相关的错误
                    error_str = str(e)
                    if any(keyword in error_str.lower() for keyword in ["websocket", "socket", "connection", "broken pipe", "clienterror"]):
                        # 完全忽略WebSocket连接错误
                        pass
                    else:
                        print(f"[CCXGroupExecutor] 发送消息失败: {e}")
            
            server.send_sync = patched_send_sync
        except Exception as e:
            print(f"[CCXGroupExecutor] 设置中断监听器失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _cancel_all_on_interrupt(self):
        """响应全局中断，取消所有正在运行的后台任务"""
        with self.task_lock:
            for node_id, task_info in list(self.running_tasks.items()):
                if task_info.get("status") == "running" and not task_info.get("cancel"):
                    task_info["cancel"] = True
    
    def execute_in_background(self, node_id, execution_list, full_api_prompt):
        """启动后台执行线程
        
        Args:
            node_id: 节点 ID
            execution_list: 执行列表，每项包含 group_name, repeat_count, delay_seconds, output_node_ids
            full_api_prompt: 前端生成的完整 API prompt（已经是正确格式）
        """
        with self.task_lock:
            # 检查是否有真正运行的线程
            if node_id in self.running_tasks:
                task = self.running_tasks[node_id]
                # 检查线程是否还在运行
                if task.get("thread") and task["thread"].is_alive():
                    print(f"[CCXGroupExecutor] 任务 {node_id} 已经在运行，拒绝重复启动")
                    return False
                # 如果线程已经结束，清理旧任务状态
                print(f"[CCXGroupExecutor] 清理任务 {node_id} 的旧状态")
                del self.running_tasks[node_id]
            
            # 清理可能存在的中断状态（即使是其他任务的）
            if hasattr(self, "interrupted_prompts"):
                print(f"[CCXGroupExecutor] 清理所有旧的中断状态")
                self.interrupted_prompts.clear()
            
            thread = threading.Thread(
                target=self._execute_task,
                args=(node_id, execution_list, full_api_prompt),
                daemon=True
            )
            thread.start()
            
            self.running_tasks[node_id] = {
                "thread": thread,
                "status": "running",
                "cancel": False,
                "start_time": time.time()  # 添加开始时间，便于调试
            }
            
            print(f"[CCXGroupExecutor] 成功启动任务 {node_id}，线程 ID: {thread.ident}")
            return True
    
    def cancel_task(self, node_id):
        """取消任务"""
        with self.task_lock:
            if node_id in self.running_tasks:
                self.running_tasks[node_id]["cancel"] = True
                
                # 中断当前正在执行的任务
                try:
                    server = PromptServer.instance
                    server.send_sync("interrupt", {})
                except Exception as e:
                    print(f"[CCXGroupExecutor] 发送中断信号失败: {e}")
                
                return True
            return False
    
    def _execute_task(self, node_id, execution_list, full_api_prompt):
        """后台执行任务的核心逻辑
        
        Args:
            node_id: 节点 ID
            execution_list: 执行列表
            full_api_prompt: 前端生成的完整 API prompt
        """
        print(f"[CCXGroupExecutor] 开始执行任务 node_id={node_id}, 执行列表长度={len(execution_list)}")
        print(f"[CCXGroupExecutor] 完整执行列表: {execution_list}")
        
        # 验证执行列表
        if not isinstance(execution_list, list) or len(execution_list) == 0:
            print(f"[CCXGroupExecutor] 无效的执行列表: {execution_list}")
            return
        
        # 打印执行列表详情，方便调试
        valid_execution_count = 0
        for i, exec_item in enumerate(execution_list):
            group_name = exec_item.get("group_name", "")
            output_node_ids = exec_item.get("output_node_ids", [])
            repeat_count = exec_item.get("repeat_count", 1)
            delay_seconds = exec_item.get("delay_seconds", 0)
            
            is_valid = True
            if group_name != "__delay__" and not output_node_ids:
                is_valid = False
            
            status = "有效" if is_valid else "无效"
            print(f"[CCXGroupExecutor] 执行项 {i+1}/{len(execution_list)}: group_name={group_name}, output_node_ids={output_node_ids}, repeat_count={repeat_count}, delay_seconds={delay_seconds} [{status}]")
            
            if is_valid:
                valid_execution_count += 1
        
        if valid_execution_count == 0:
            print(f"[CCXGroupExecutor] 没有有效的执行项，任务将终止")
            return
        
        try:
            # 确保任务开始时的状态是干净的
            with self.task_lock:
                if node_id in self.running_tasks:
                    print(f"[CCXGroupExecutor] 重置任务 {node_id} 的取消标志")
                    self.running_tasks[node_id]["cancel"] = False
                    
            # 清理可能存在的旧中断状态
            if hasattr(self, "interrupted_prompts"):
                print(f"[CCXGroupExecutor] 清理旧的中断状态")
                self.interrupted_prompts.clear()
            
            # 遍历执行列表中的每个执行项
            for item_index, exec_item in enumerate(execution_list):
                # 检查取消标志
                if self.running_tasks.get(node_id, {}).get("cancel"):
                    print(f"[CCXGroupExecutor] 任务被取消")
                    break
                
                group_name = exec_item.get("group_name", "")
                repeat_count = int(exec_item.get("repeat_count", 1))
                delay_seconds = float(exec_item.get("delay_seconds", 0))
                output_node_ids = exec_item.get("output_node_ids", [])
                
                print(f"\n[CCXGroupExecutor] ====== 处理执行项 {item_index+1}/{len(execution_list)} ======")
                print(f"[CCXGroupExecutor] group_name={group_name}, repeat_count={repeat_count}, delay_seconds={delay_seconds}")
                print(f"[CCXGroupExecutor] output_node_ids={output_node_ids}")
                
                # 验证执行项
                if group_name != "__delay__" and (not group_name or not output_node_ids):
                    print(f"[CCXGroupExecutor] 跳过无效执行项: group_name={group_name}, output_node_ids={output_node_ids}")
                    continue
                
                # 处理延迟
                if group_name == "__delay__":
                    print(f"[CCXGroupExecutor] 执行延迟: {delay_seconds}秒")
                    if delay_seconds > 0 and not self.running_tasks.get(node_id, {}).get("cancel"):
                        # 分段延迟，以便能快速响应取消
                        delay_steps = int(delay_seconds * 2)  # 每 0.5 秒检查一次
                        for step in range(delay_steps):
                            if self.running_tasks.get(node_id, {}).get("cancel"):
                                print(f"[CCXGroupExecutor] 延迟期间任务被取消")
                                break
                            time.sleep(0.5)
                            if (step + 1) % 2 == 0:  # 每1秒打印一次延迟进度
                                print(f"[CCXGroupExecutor] 延迟进度: {int((step + 1) * 0.5)}秒/{delay_seconds}秒")
                    continue
                
                # 执行 repeat_count 次
                for repeat_index in range(repeat_count):
                    # 检查取消标志
                    if self.running_tasks.get(node_id, {}).get("cancel"):
                        print(f"[CCXGroupExecutor] 任务被取消")
                        break
                    
                    if repeat_count > 1:
                        print(f"[CCXGroupExecutor] 执行组 '{group_name}' ({repeat_index+1}/{repeat_count})")
                    else:
                        print(f"[CCXGroupExecutor] 执行组 '{group_name}'")
                    
                    # 从完整 prompt 中筛选出该组需要的节点
                    print(f"[CCXGroupExecutor] 从完整 prompt 中筛选节点，输出节点 ID: {output_node_ids}")
                    prompt = filter_prompt_for_nodes(full_api_prompt, output_node_ids)
                    
                    if not prompt:
                        print(f"[CCXGroupExecutor] 筛选 prompt 失败，跳过此执行")
                        continue
                    
                    print(f"[CCXGroupExecutor] 筛选出 {len(prompt)} 个节点")
                    
                    # 处理随机种子：为每个有 seed 参数的节点生成新的随机值
                    print(f"[CCXGroupExecutor] 处理随机种子")
                    seed_nodes = 0
                    for node_id_str, node_data in prompt.items():
                        if "seed" in node_data.get("inputs", {}):
                            new_seed = random.randint(0, 0xffffffffffffffff)
                            prompt[node_id_str]["inputs"]["seed"] = new_seed
                            seed_nodes += 1
                        # 也处理 noise_seed（某些节点使用这个名称）
                        if "noise_seed" in node_data.get("inputs", {}):
                            new_seed = random.randint(0, 0xffffffffffffffff)
                            prompt[node_id_str]["inputs"]["noise_seed"] = new_seed
                            seed_nodes += 1
                    
                    if seed_nodes > 0:
                        print(f"[CCXGroupExecutor] 更新了 {seed_nodes} 个节点的随机种子")
                    
                    # 提交到队列
                    print(f"[CCXGroupExecutor] 提交 prompt 到队列")
                    task_info = self._queue_prompt(prompt)
                    
                    if task_info:
                        number, prompt_id = task_info
                        print(f"[CCXGroupExecutor] Prompt 提交成功，number={number}, ID: {prompt_id}")
                        # 等待执行完成（返回是否检测到中断）
                        was_interrupted = self._wait_for_completion(task_info, node_id)
                        
                        # 如果等待期间检测到中断，立即退出
                        if was_interrupted:
                            print(f"[CCXGroupExecutor] 执行中断")
                            # 使用return而不是break，确保能正确清理资源
                            return
                    else:
                        print(f"[CCXGroupExecutor] 提交 prompt 失败")
                    
                    # 延迟（支持中断）
                    if delay_seconds > 0 and repeat_index < repeat_count - 1:
                        print(f"[CCXGroupExecutor] 组执行之间的延迟: {delay_seconds}秒")
                        if not self.running_tasks.get(node_id, {}).get("cancel"):
                            # 分段延迟，以便能快速响应取消
                            delay_steps = int(delay_seconds * 2)  # 每 0.5 秒检查一次
                            for step in range(delay_steps):
                                if self.running_tasks.get(node_id, {}).get("cancel"):
                                    print(f"[CCXGroupExecutor] 延迟期间任务被取消")
                                    break
                                time.sleep(0.5)
                                if (step + 1) % 2 == 0:  # 每1秒打印一次延迟进度
                                    print(f"[CCXGroupExecutor] 延迟进度: {int((step + 1) * 0.5)}秒/{delay_seconds}秒")
            
            if self.running_tasks.get(node_id, {}).get("cancel"):
                print(f"[CCXGroupExecutor] 任务已取消")
            else:
                print(f"[CCXGroupExecutor] 所有执行项处理完成，任务执行结束")
            
        except Exception as e:
            print(f"[CCXGroupExecutor] 后台执行出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            with self.task_lock:
                # 任务完成后从 running_tasks 中删除
                if node_id in self.running_tasks:
                    print(f"[CCXGroupExecutor] 从 running_tasks 中删除任务 {node_id}")
                    del self.running_tasks[node_id]
                
                # 确保中断状态也被清理
                if hasattr(self, "interrupted_prompts"):
                    print(f"[CCXGroupExecutor] 清理最终的中断状态")
                    self.interrupted_prompts.clear()
                
                print(f"[CCXGroupExecutor] 任务 {node_id} 的所有状态已清理")
    
    def _queue_prompt(self, prompt):
        """提交 prompt 到队列"""
        try:
            # 基本验证：确保prompt不为空
            if not prompt or not isinstance(prompt, dict) or len(prompt) == 0:
                print(f"[CCXGroupExecutor] Prompt 为空或格式无效: {prompt}")
                return None
            
            server = PromptServer.instance
            prompt_id = str(uuid.uuid4())
            
            print(f"[CCXGroupExecutor] 开始提交 prompt，包含 {len(prompt)} 个节点，prompt_id={prompt_id}")
            
            # 验证 prompt（validate_prompt 是异步函数，需要在事件循环中运行）
            try:
                loop = server.loop
                # 在事件循环中运行异步函数
                print(f"[CCXGroupExecutor] 开始验证 prompt，包含节点: {list(prompt.keys())}")
                valid = asyncio.run_coroutine_threadsafe(
                    execution.validate_prompt(prompt_id, prompt, None),
                    loop
                ).result(timeout=30)
            except Exception as validate_error:
                print(f"[CCXGroupExecutor] Prompt 验证出错: {validate_error}")
                import traceback
                traceback.print_exc()
                return None
            
            if not valid[0]:
                print(f"[CCXGroupExecutor] Prompt 验证失败: {valid[1]}")
                return None
            
            # 获取输出节点列表
            outputs_to_execute = list(valid[2])
            print(f"[CCXGroupExecutor] Prompt 验证通过，输出节点数量: {len(outputs_to_execute)}")
            
            # 确保输出节点列表不为空
            if not outputs_to_execute:
                print(f"[CCXGroupExecutor] 警告：没有找到输出节点，这可能导致执行失败")
                
                # 尝试从prompt中找到可能的输出节点
                possible_outputs = []
                for node_id, node_data in prompt.items():
                    # 检查是否是已知的输出节点类型
                    class_type = node_data.get('class_type', '')
                    if class_type in ['SaveImage', 'PreviewImage']:
                        possible_outputs.append(node_id)
                    # 也检查是否有'output_node'属性的节点
                    if node_data.get('output_node') == True:
                        possible_outputs.append(node_id)
                    # 检查是否有'outputs'但没有'inputs'的节点
                    if node_data.get('outputs') and not node_data.get('inputs'):
                        possible_outputs.append(node_id)
                        
                if possible_outputs:
                    # 去重
                    outputs_to_execute = list(set(possible_outputs))
                    print(f"[CCXGroupExecutor] 尝试使用可能的输出节点: {outputs_to_execute}")
                else:
                    # 最后尝试：使用prompt中的最后一个节点作为输出节点
                    if len(prompt) > 0:
                        last_node_id = list(prompt.keys())[-1]
                        outputs_to_execute = [last_node_id]
                        print(f"[CCXGroupExecutor] 没有找到明确的输出节点，使用最后一个节点 {last_node_id} 作为输出")
                    else:
                        print(f"[CCXGroupExecutor] 没有找到任何可能的输出节点，跳过此prompt")
                        return None
            
            # 构建队列项（确保与ComfyUI的预期格式完全一致）
            # 格式：(number, prompt_id, prompt, extra_data, outputs_to_execute, sensitive)
            extra_data = {}
            sensitive = {}
            
            # 验证队列项格式（先使用临时number=0进行验证）
            temp_queue_item = (0, prompt_id, prompt, extra_data, outputs_to_execute, sensitive)
            print(f"[CCXGroupExecutor] 构建队列项: prompt_id={prompt_id}, 输出节点={outputs_to_execute}")
            
            # 验证队列项格式
            if not isinstance(temp_queue_item, tuple) or len(temp_queue_item) != 6:
                print(f"[CCXGroupExecutor] 队列项格式错误: {temp_queue_item}")
                return None
            
            # 只有在所有验证都通过后才递增number
            number = server.number
            server.number += 1
            
            # 使用正确的number构建最终队列项
            queue_item = (number, prompt_id, prompt, extra_data, outputs_to_execute, sensitive)
            print(f"[CCXGroupExecutor] 构建队列项完成: number={number}, prompt_id={prompt_id}, 输出节点={outputs_to_execute}")
            
            # 提交到队列
            server.prompt_queue.put(queue_item)
            
            print(f"[CCXGroupExecutor] Prompt 成功提交到队列，number={number}, prompt_id={prompt_id}")
            
            # 返回任务编号和prompt_id，用于更准确的状态跟踪
            return (number, prompt_id)
            
        except Exception as e:
            # 修复：在任何异常情况下都回滚server.number的递增
            if 'server' in locals() and hasattr(server, 'number'):
                # 只有在已经递增过number的情况下才回滚
                # 通过检查number是否大于原始值来判断
                if 'number' in locals() and server.number > number:
                    server.number -= 1
                    print(f"[CCXGroupExecutor] 异常回滚 number 到 {server.number}")
            print(f"[CCXGroupExecutor] 提交队列失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _wait_for_completion(self, task_info, node_id):
        """等待 prompt 执行完成，同时响应取消请求
        参数: task_info 是包含 (number, prompt_id) 的元组
        返回: True 如果检测到中断，False 正常完成
        """
        try:
            server = PromptServer.instance
            number, prompt_id = task_info
            
            print(f"[CCXGroupExecutor] 等待任务完成: number={number}, prompt_id={prompt_id}")
            
            wait_start_time = time.time()
            max_wait_time = 300  # 最大等待时间5分钟，避免无限等待
            
            # 连续检查的计数
            consecutive_checks = 0
            max_consecutive_checks = 5  # 最多连续检查5次
            
            while True:
                # 检查是否超过最大等待时间
                if time.time() - wait_start_time > max_wait_time:
                    print(f"[CCXGroupExecutor] 任务等待超时 ({max_wait_time}秒): number={number}, prompt_id={prompt_id}")
                    return False  # 超时视为正常完成，但实际上可能有问题
                
                # 检查任务是否已经被移除（可能任务已经完成但我们不知道）
                if node_id not in self.running_tasks:
                    print(f"[CCXGroupExecutor] 任务节点 {node_id} 已不在运行任务列表中，可能已被清理")
                    return False
                
                # 检查这个 prompt 是否被中断
                if prompt_id in self.interrupted_prompts:
                    # 设置任务取消标志
                    with self.task_lock:
                        if node_id in self.running_tasks:
                            self.running_tasks[node_id]["cancel"] = True
                    # 从中断集合中移除
                    self.interrupted_prompts.discard(prompt_id)
                    print(f"[CCXGroupExecutor] 任务被中断: number={number}, prompt_id={prompt_id}")
                    return True  # 返回中断状态
                
                # 检查是否被取消
                if self.running_tasks.get(node_id, {}).get("cancel"):
                    # 从队列中删除这个 prompt（如果还在队列中）
                    try:
                        def should_delete(item):
                            return len(item) >= 2 and (item[1] == prompt_id or item[0] == number)
                        server.prompt_queue.delete_queue_item(should_delete)
                    except Exception as del_error:
                        print(f"[CCXGroupExecutor] 删除队列项时出错: {del_error}")
                    print(f"[CCXGroupExecutor] 任务被取消: number={number}, prompt_id={prompt_id}")
                    return True  # 返回中断状态
                
                # 检查是否在历史记录中（表示已完成）
                if prompt_id in server.prompt_queue.history:
                    # 检查是否是因为中断而完成的
                    if prompt_id in self.interrupted_prompts:
                        self.interrupted_prompts.discard(prompt_id)
                        print(f"[CCXGroupExecutor] 任务在历史记录中但被中断: number={number}, prompt_id={prompt_id}")
                        return True
                    print(f"[CCXGroupExecutor] 任务正常完成: number={number}, prompt_id={prompt_id}")
                    return False  # 正常完成
                
                # 检查是否还在队列中
                running, pending = server.prompt_queue.get_current_queue()
                
                in_queue = False
                
                # 检查运行队列
                for item in running:
                    if len(item) >= 2 and (item[1] == prompt_id or item[0] == number):
                        in_queue = True
                        print(f"[CCXGroupExecutor] 任务仍在运行队列中: number={number}, prompt_id={prompt_id}")
                        consecutive_checks = 0  # 重置检查计数
                        break
                
                # 检查等待队列
                if not in_queue:
                    for item in pending:
                        if len(item) >= 2 and (item[1] == prompt_id or item[0] == number):
                            in_queue = True
                            print(f"[CCXGroupExecutor] 任务在等待队列中: number={number}, prompt_id={prompt_id}")
                            consecutive_checks = 0  # 重置检查计数
                            break
                
                # 如果任务不在队列中且不在历史记录中，增加检查计数
                if not in_queue and prompt_id not in server.prompt_queue.history:
                    consecutive_checks += 1
                    print(f"[CCXGroupExecutor] 任务不在队列中，已连续检查 {consecutive_checks}/{max_consecutive_checks} 次: number={number}, prompt_id={prompt_id}")
                    
                    # 只有连续检查次数达到最大值，才认为任务已经完成
                    if consecutive_checks >= max_consecutive_checks:
                        print(f"[CCXGroupExecutor] 任务连续 {max_consecutive_checks} 次不在队列中且不在历史记录中，认为已完成: number={number}, prompt_id={prompt_id}")
                        return False
                else:
                    consecutive_checks = 0  # 重置检查计数
                
                # 正常等待，避免太频繁检查
                time.sleep(1.0)  # 增加等待时间到1秒，减少检查频率
                
        except Exception as e:
            print(f"[CCXGroupExecutor] 等待执行完成时出错: {e}")
            import traceback
            traceback.print_exc()
            return False

# 全局后台执行器实例
_backend_executor = GroupExecutorBackend()

# ============ 节点定义 ============

import re

class CCXGroupExecutorSingle:
    def __init__(self):
        # 添加执行状态管理
        self.is_executing = False
        self.execution_lock = threading.Lock()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "group_name": ("STRING", {"multiline": True}),
                "repeat_count": ("INT", {"default": 1, "min": 1, "max": 100, "step": 1}),
                "delay_seconds": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 60.0, "step": 0.1}),
            },
            "optional": {
                "signal": ("SIGNAL",),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID"
            }
        }

    RETURN_TYPES = ("SIGNAL",)
    FUNCTION = "execute_group"
    CATEGORY = "Update of SD-PPP Plugin"

    def execute_group(self, group_name, repeat_count, delay_seconds, signal=None, unique_id=None):
        try:
            # 使用锁确保只有一个执行请求通过
            with self.execution_lock:
                if self.is_executing:
                    print(f"[CCXGroupExecutorSingle] 节点已经在执行中，拒绝重复执行请求 (unique_id={unique_id})")
                    # 如果有信号输入，直接返回信号
                    if signal is not None:
                        return (signal,)
                    # 否则返回空信号
                    return (([],),)
                
                # 设置执行状态
                self.is_executing = True
            # 将多行输入拆分为多个组（支持逗号和换行分隔）
            group_names = [name.strip() for name in re.split(r'[,\n]+', group_name) if name.strip()]
            execution_list = []

            # 为每个组创建执行项
            for group in group_names:
                execution_list.append({
                    "group_name": group,
                    "repeat_count": repeat_count,      
                    "delay_seconds": delay_seconds     
                })

            # 如果有信号输入，将信号追加到新执行列表后面（正确的执行顺序：新组先执行，然后执行信号中的组）
            if signal is not None:
                if isinstance(signal, list):
                    # 将信号中的执行项追加到新执行列表后面
                    result = execution_list.copy()
                    result.extend(signal)
                    return (result,)
                else:
                    # 如果信号不是列表，将信号作为单个执行项追加到新执行列表后面
                    result = execution_list.copy()
                    result.append(signal)
                    return (result,)

            # 如果没有信号输入，直接返回执行列表        
            return (execution_list,)

        except Exception as e:
            print(f"[GroupExecutorMulti {unique_id}] 错误: {e}")
            import traceback
            traceback.print_exc()
            return ({"error": str(e)},)
        finally:
            # 无论执行成功还是失败，都重置执行状态
            with self.execution_lock:
                self.is_executing = False
class CCXGroupExecutorSender:
    """执行信号发送节点"""
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "signal": ("SIGNAL",),
                "execution_mode": (["前端执行", "后台执行"], {"default": "后台执行"}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO"
            }
        }
    
    RETURN_TYPES = () 
    FUNCTION = "execute"
    CATEGORY = CATEGORY_TYPE
    OUTPUT_NODE = True

    def execute(self, signal, execution_mode, unique_id=None, prompt=None, extra_pnginfo=None):
        try:
            if not signal:
                raise ValueError("没有收到执行信号")

            execution_list = signal if isinstance(signal, list) else [signal]

            if execution_mode == "后台执行":
                # 后台执行模式：通知前端生成 API prompt 并发送给后端
                PromptServer.instance.send_sync(
                    "ccx_execute_group_list_backend", {
                        "node_id": unique_id,
                        "execution_list": execution_list
                    }
                )
                
            else:
                # 前端执行模式（原有方式）
                PromptServer.instance.send_sync(
                    "ccx_execute_group_list", {
                        "node_id": unique_id,
                        "execution_list": execution_list
                    }
                )
            
            return ()  

        except Exception as e:
            print(f"[CCXGroupExecutor] 执行错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return ()


        

CONFIG_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "group_configs")
os.makedirs(CONFIG_DIR, exist_ok=True)

routes = PromptServer.instance.routes

@routes.post("/ccx_group_executor/execute_backend")
async def execute_backend(request):
    """接收前端发送的执行请求，在后台执行组"""
    try:
        data = await request.json()
        node_id = data.get("node_id")
        execution_list = data.get("execution_list", [])
        full_api_prompt = data.get("api_prompt", {})
        
        if not node_id:
            return web.json_response({"status": "error", "message": "缺少 node_id"}, status=400)
        
        if not execution_list:
            return web.json_response({"status": "error", "message": "执行列表为空"}, status=400)
        
        if not full_api_prompt:
            return web.json_response({"status": "error", "message": "缺少 API prompt"}, status=400)
        
        print(f"[CCXGroupExecutor] 收到后台执行请求: node_id={node_id}, 执行项数={len(execution_list)}")
        
        # 启动后台执行
        success = _backend_executor.execute_in_background(
            node_id,
            execution_list,
            full_api_prompt
        )
        
        if success:
            return web.json_response({"status": "success", "message": "后台执行已启动"})
        else:
            return web.json_response({"status": "error", "message": "已有任务在执行中"}, status=409)
            
    except Exception as e:
        print(f"[CCXGroupExecutor] 后台执行请求处理失败: {e}")
        import traceback
        traceback.print_exc()
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@routes.get("/ccx_group_executor/configs")
async def get_configs(request):
    try:

        configs = []
        for filename in os.listdir(CONFIG_DIR):
            if filename.endswith('.json'):
                configs.append({
                    "name": filename[:-5]
                })
        return web.json_response({"status": "success", "configs": configs})
    except Exception as e:
        print(f"[CCXGroupExecutor] 获取配置失败: {str(e)}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@routes.post("/ccx_group_executor/configs")
async def save_config(request):
    try:
        print("[CCXGroupExecutor] 收到保存配置请求")
        data = await request.json()
        config_name = data.get('name')
        if not config_name:
            return web.json_response({"status": "error", "message": "配置名称不能为空"}, status=400)
            
        safe_name = "".join(c for c in config_name if c.isalnum() or c in (' ', '-', '_'))
        filename = os.path.join(CONFIG_DIR, f"{safe_name}.json")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print(f"[CCXGroupExecutor] 配置已保存: {filename}")
        return web.json_response({"status": "success"})
    except json.JSONDecodeError as e:
        print(f"[CCXGroupExecutor] JSON解析错误: {str(e)}")
        return web.json_response({"status": "error", "message": f"JSON格式错误: {str(e)}"}, status=400)
    except Exception as e:
        print(f"[CCXGroupExecutor] 保存配置失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@routes.get('/ccx_group_executor/configs/{name}')
async def get_config(request):
    try:
        config_name = request.match_info.get('name')
        if not config_name:
            return web.json_response({"error": "配置名称不能为空"}, status=400)
            
        filename = os.path.join(CONFIG_DIR, f"{config_name}.json")
        if not os.path.exists(filename):
            return web.json_response({"error": "配置不存在"}, status=404)
            
        with open(filename, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        return web.json_response(config)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

@routes.delete('/ccx_group_executor/configs/{name}')
async def delete_config(request):
    try:
        config_name = request.match_info.get('name')
        if not config_name:
            return web.json_response({"error": "配置名称不能为空"}, status=400)
            
        filename = os.path.join(CONFIG_DIR, f"{config_name}.json")
        if not os.path.exists(filename):
            return web.json_response({"error": "配置不存在"}, status=404)
            
        os.remove(filename)
        return web.json_response({"status": "success"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# 导出节点映射
NODE_CLASS_MAPPINGS = {
    "CCXGroupExecutorSingle": CCXGroupExecutorSingle,
    "CCXGroupExecutorSender": CCXGroupExecutorSender
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CCXGroupExecutorSingle": "🎈CCX Group Executor (Single)",
    "CCXGroupExecutorSender": "🎈CCX Group Executor (Sender)"
}
