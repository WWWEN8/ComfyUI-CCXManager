import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { queueManager, getOutputNodes } from "./queue_utils.js";

// 全局标志，用于确保事件监听器只被注册一次
let eventListenersRegistered = false;

// 全局执行锁，确保同一时间只有一个执行请求在处理
let globalExecutionLock = false;

app.registerExtension({
    name: "CCXGroupExecutorSender",
    async setup() {
        // 修复：在图加载完成后重置所有GroupExecutorSender节点的状态
        app.addEventListener("graphLoaded", () => {
            console.log("[CCXGroupExecutorSender] 图加载完成，重置所有发送者节点状态...");
            const senderNodes = app.graph._nodes.filter(n => n.type === "CCXGroupExecutorSender");
            senderNodes.forEach(node => {
                if (node.resetExecutionStatus) {
                    node.resetExecutionStatus();
                } else {
                    // 如果没有resetExecutionStatus方法，直接重置属性
                    node.properties.isExecuting = false;
                    node.properties.isCancelling = false;
                    node.properties.statusText = "";
                    node.properties.showStatus = false;
                    node.setDirtyCanvas(true, true);
                }
            });
        });
    },
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "CCXGroupExecutorSender") {
            nodeType.prototype.onNodeCreated = function() {
                this.properties = {
                    ...this.properties,
                    isExecuting: false,
                    isCancelling: false,
                    statusText: "",
                    showStatus: false
                };
                
                this.size = this.computeSize();
            };
            
            // 在节点注册时重置所有执行状态
            nodeType.prototype.onAddedToGraph = function() {
                this.properties = {
                    ...this.properties,
                    isExecuting: false,
                    isCancelling: false,
                    statusText: "",
                    showStatus: false
                };
            };
            
            // 修复：确保执行状态不会被持久化到json文件中
            const originalSerialize = nodeType.prototype.serialize;
            nodeType.prototype.serialize = function() {
                const data = originalSerialize?.apply(this, arguments) || {};
                if (data.properties) {
                    // 移除执行状态相关的属性，避免持久化
                    delete data.properties.isExecuting;
                    delete data.properties.isCancelling;
                    delete data.properties.statusText;
                    delete data.properties.showStatus;
                }
                return data;
            };
            
            // 修复：在节点配置时确保状态正确初始化
            const originalConfigure = nodeType.prototype.configure;
            nodeType.prototype.configure = function(info) {
                if (originalConfigure) {
                    originalConfigure.apply(this, arguments);
                }
                // 强制重置执行状态
                this.properties.isExecuting = false;
                this.properties.isCancelling = false;
                this.properties.statusText = "";
                this.properties.showStatus = false;
            };

            const onDrawForeground = nodeType.prototype.onDrawForeground;
            nodeType.prototype.onDrawForeground = function(ctx) {
                const r = onDrawForeground?.apply?.(this, arguments);

                if (!this.flags.collapsed && this.properties.showStatus) {
                    const text = this.properties.statusText;
                    if (text) {
                        ctx.save();

                        ctx.font = "bold 30px sans-serif";
                        ctx.textAlign = "center";
                        ctx.textBaseline = "middle";

                        ctx.fillStyle = this.properties.isExecuting ? "dodgerblue" : "limegreen";

                        const centerX = this.size[0] / 2;
                        const centerY = this.size[1] / 2 + 10; 

                        ctx.fillText(text, centerX, centerY);
                        
                        ctx.restore();
                    }
                }

                return r;
            };

            nodeType.prototype.computeSize = function() {
                return [400, 100]; // 固定宽度和高度
            };

            nodeType.prototype.updateStatus = function(text) {
                this.properties.statusText = text;
                this.properties.showStatus = true;
                this.setDirtyCanvas(true, true);
            };

            nodeType.prototype.resetStatus = function() {
                this.properties.statusText = "";
                this.properties.showStatus = false;
                this.setDirtyCanvas(true, true);
            };

            nodeType.prototype.getGroupOutputNodes = function(groupName) {
                console.log(`[CCXGroupExecutorSender] 获取组 "${groupName}" 的输出节点`);
                
                // 首先尝试通过标题查找组
                let group = app.graph._groups.find(g => g.title === groupName);
                
                // 如果找不到，尝试通过ID查找组（可能组的标题有空格或特殊字符）
                if (!group) {
                    group = app.graph._groups.find(g => g.id === groupName);
                }
                
                if (!group) {
                    console.warn(`[CCXGroupExecutorSender] 未找到名为 "${groupName}" 的组`);
                    return [];
                }
                
                console.log(`[CCXGroupExecutorSender] 找到组: ID=${group.id}, 标题="${group.title}", 边界=${JSON.stringify(group._bounding)}`);
                
                // 确保组的边界和内部节点是最新的
                if (group.recomputeInsideNodes) {
                    console.log(`[CCXGroupExecutorSender] 调用 recomputeInsideNodes 更新组 ${group.id} 的内部节点`);
                    group.recomputeInsideNodes();
                }
                
                // 强制重新计算组内节点，确保始终使用最新的节点列表
                let groupNodes = [];
                for (const node of app.graph._nodes) {
                    if (!node || !node.pos) continue;
                    
                    const nodeBound = node.getBounding();
                    if (LiteGraph.overlapBounding(group._bounding, nodeBound)) {
                        groupNodes.push(node);
                        console.log(`[CCXGroupExecutorSender] 节点 ${node.id} (${node.type}) 位于组内，位置: ${JSON.stringify(node.pos)}`);
                    }
                }
                
                group._nodes = groupNodes;
                console.log(`[CCXGroupExecutorSender] 组 "${groupName}" 包含 ${groupNodes.length} 个节点`);
                
                // 筛选出输出节点
                const outputNodes = this.getOutputNodes(groupNodes);
                
                // 额外验证：确保输出节点真的在组内
                const validOutputNodes = outputNodes.filter(node => {
                    const nodeBound = node.getBounding();
                    const isInside = LiteGraph.overlapBounding(group._bounding, nodeBound);
                    if (!isInside) {
                        console.warn(`[CCXGroupExecutorSender] 输出节点 ${node.id} 标记为组内节点，但实际上不在组边界内`);
                    }
                    return isInside;
                });
                
                console.log(`[CCXGroupExecutorSender] 组 "${groupName}" 找到 ${validOutputNodes.length} 个有效输出节点:`, validOutputNodes.map(n => ({id: n.id, type: n.type})));
                
                return validOutputNodes;
            };

            nodeType.prototype.getOutputNodes = function(nodes) {
                return nodes.filter((n) => {
                    return n.mode !== LiteGraph.NEVER && 
                           n.constructor.nodeData?.output_node === true;
                });
            };

            // 后台执行：生成 API prompt 并发送给后端
            nodeType.prototype.executeInBackend = async function(executionList) {
                try {
                    // 修复：检查节点是否已经在执行中，如果是则直接返回，避免重复执行
                    if (this.properties.isExecuting) {
                        console.warn('[CCXGroupExecutorSender] 节点已经在执行中，拒绝重复执行请求');
                        return false;
                    }
                    
                    // 设置执行状态
                    this.properties.isExecuting = true;
                    
                    console.log(`[CCXGroupExecutorSender] 开始后台执行，执行列表长度: ${executionList.length}`);
                    console.log(`[CCXGroupExecutorSender] 原始执行列表:`, executionList);
                    
                    // 1. 为每个执行项收集输出节点 ID（在生成 prompt 之前，确保节点信息准确）
                    const enrichedExecutionList = [];
                    let hasValidExecutionItem = false;
                    
                    // 保存原始的节点模式，确保在获取输出节点时所有节点都能被检测到
                    const originalModes = {};
                    const allNodes = app.graph._nodes;
                    
                    // 临时将所有节点模式设置为ALWAYS，确保输出节点检测准确
                    allNodes.forEach(node => {
                        originalModes[node.id] = node.mode;
                        node.mode = LiteGraph.ALWAYS;
                    });
                    
                    try {
                        // 遍历原始执行列表，保持顺序
                        for (let i = 0; i < executionList.length; i++) {
                            const exec = executionList[i];
                            const groupName = exec.group_name || '';
                            
                            console.log(`[CCXGroupExecutorSender] 处理执行项 ${i + 1}/${executionList.length}: group_name=${groupName}`);
                            
                            // 延迟项直接添加
                            if (groupName === "__delay__") {
                                console.log(`[CCXGroupExecutorSender] 添加延迟项: ${exec.delay_seconds}秒`);
                                enrichedExecutionList.push(exec);
                                hasValidExecutionItem = true;
                                continue;
                            }
                            
                            if (!groupName) {
                                console.warn(`[CCXGroupExecutorSender] 跳过空的组名称`);
                                continue;
                            }
                            
                            // 获取组内的输出节点
                            const outputNodes = this.getGroupOutputNodes(groupName);
                            if (!outputNodes || outputNodes.length === 0) {
                                console.warn(`[CCXGroupExecutorSender] 组 "${groupName}" 中没有输出节点，跳过该组`);
                                continue;
                            }
                            
                            const outputNodeIds = outputNodes.map(n => n.id);
                            console.log(`[CCXGroupExecutorSender] 组 "${groupName}" 有 ${outputNodeIds.length} 个输出节点: ${outputNodeIds}`);
                            
                            const enrichedExec = {
                                ...exec,
                                output_node_ids: outputNodeIds
                            };
                            
                            enrichedExecutionList.push(enrichedExec);
                            hasValidExecutionItem = true;
                            console.log(`[CCXGroupExecutorSender] 已添加执行项到丰富列表:`, enrichedExec);
                        }
                    } finally {
                        // 恢复原始节点模式
                        allNodes.forEach(node => {
                            if (originalModes[node.id] !== undefined) {
                                node.mode = originalModes[node.id];
                            }
                        });
                        console.log(`[CCXGroupExecutorSender] 已恢复所有节点的原始模式（输出节点检测阶段）`);
                    }
                    
                    if (!hasValidExecutionItem) {
                        throw new Error("没有有效的执行项，请检查组名称和输出节点设置");
                    }
                    
                    console.log(`[CCXGroupExecutorSender] 完成执行列表丰富化，有效执行项数量: ${enrichedExecutionList.length}`);
                    console.log(`[CCXGroupExecutorSender] 丰富后的执行列表:`, enrichedExecutionList);
                    
                    // 2. 生成完整的 API prompt（在收集完所有节点信息后）
                    console.log(`[CCXGroupExecutorSender] 生成完整的 API prompt...`);
                    
                    // 保存原始的节点模式，确保所有节点都被包含在API prompt中
                    const originalModesApi = {};
                    const allNodesApi = app.graph._nodes;
                    
                    // 临时将所有节点模式设置为ALWAYS，确保它们都被包含在API prompt中
                    allNodesApi.forEach(node => {
                        originalModesApi[node.id] = node.mode;
                        node.mode = LiteGraph.ALWAYS;
                    });
                    
                    let fullApiPrompt;
                    try {
                        // 生成完整的API prompt
                        const { output } = await app.graphToPrompt();
                        fullApiPrompt = output;
                        console.log(`[CCXGroupExecutorSender] API prompt 生成完成，包含 ${Object.keys(fullApiPrompt).length} 个节点`);
                        console.log(`[CCXGroupExecutorSender] API prompt 包含的节点 ID:`, Object.keys(fullApiPrompt));
                    
                        // 3. 发送给后端
                        console.log(`[CCXGroupExecutorSender] 发送后台执行请求到 /ccx_group_executor/execute_backend`);
                        const response = await api.fetchApi('/ccx_group_executor/execute_backend', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                node_id: this.id,
                                execution_list: enrichedExecutionList,
                                api_prompt: fullApiPrompt
                            })
                        });
                        
                        // 检查响应状态
                        if (!response.ok) {
                            const text = await response.text();
                            console.error(`[CCXGroupExecutorSender] 服务器返回错误 ${response.status}:`, text);
                            throw new Error(`服务器错误 ${response.status}: ${text.substring(0, 200)}`);
                        }
                        
                        const result = await response.json();
                        
                        if (result.status === "success") {
                            console.log(`[CCXGroupExecutorSender] 后台执行已成功启动`);
                            return true;
                        } else {
                            console.error(`[CCXGroupExecutorSender] 后台执行启动失败:`, result.message);
                            throw new Error(result.message || "后台执行启动失败");
                        }
                    } finally {
                        // 无论成功还是失败，都恢复所有节点的原始模式
                        allNodesApi.forEach(node => {
                            if (originalModesApi[node.id] !== undefined) {
                                node.mode = originalModesApi[node.id];
                            }
                        });
                        console.log(`[CCXGroupExecutorSender] 已恢复所有节点的原始模式（API prompt生成阶段）`);
                    }
                    
                } catch (error) {
                    console.error('[CCXGroupExecutorSender] 后台执行失败:', error);
                    throw error;
                } finally {
                    // 无论执行成功还是失败，都重置执行状态
                    this.properties.isExecuting = false;
                    this.properties.isCancelling = false;
                }
            };

            nodeType.prototype.getQueueStatus = async function() {
                try {
                    const response = await api.fetchApi('/queue');
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    const data = await response.json();

                    const queueRunning = data.queue_running || [];
                    const queuePending = data.queue_pending || [];
                    
                    return {
                        isRunning: queueRunning.length > 0,
                        isPending: queuePending.length > 0,
                        runningCount: queueRunning.length,
                        pendingCount: queuePending.length,
                        rawRunning: queueRunning,
                        rawPending: queuePending
                    };
                } catch (error) {
                    console.error('[CCXGroupExecutorSender] 获取队列状态失败:', error);

                    // 修复：在获取队列状态失败时，不要默认返回队列空闲，而是假设队列可能正在运行
                    // 这样可以避免任务提交过快导致的重复Job问题
                    return {
                        isRunning: true,
                        isPending: true,
                        runningCount: 1,
                        pendingCount: 0,
                        rawRunning: [],
                        rawPending: []
                    };
                }
            };

            nodeType.prototype.waitForQueue = async function() {
                return new Promise((resolve, reject) => {
                    const checkQueue = async () => {
                        try {
                            if (this.properties.isCancelling) {
                                resolve();
                                return;
                            }
                            
                            const status = await this.getQueueStatus();

                            // 确保队列完全空闲：没有正在运行的任务，也没有待处理的任务
                            if (!status.isRunning && !status.isPending) {
                                // 添加一个小延迟，确保队列状态完全更新
                                setTimeout(() => {
                                    resolve();
                                }, 200);
                                return;
                            }

                            // 更频繁地检查队列状态，确保及时响应
                            setTimeout(checkQueue, 300);
                        } catch (error) {
                            console.warn(`[CCXGroupExecutorSender] 检查队列状态失败:`, error);
                            // 即使检查队列状态失败，也继续尝试，避免卡住
                            setTimeout(checkQueue, 300);
                        }
                    };

                    checkQueue();
                });
            };

            nodeType.prototype.cancelExecution = async function() {
                if (!this.properties.isExecuting) {
                    console.warn('[CCXGroupExecutorSender] 没有正在执行的任务');
                    return;
                }

                try {
                    this.properties.isCancelling = true;
                    this.updateStatus("正在取消执行...");
                    
                    await fetch('/interrupt', { method: 'POST' });
                    
                    this.updateStatus("已取消");
                    setTimeout(() => this.resetStatus(), 2000);
                    
                } catch (error) {
                    console.error('[CCXGroupExecutorSender] 取消执行时出错:', error);
                    this.updateStatus(`取消失败: ${error.message}`);
                }
            };

            // 确保事件监听器只被注册一次
            if (!eventListenersRegistered) {
                // 包装fetchApi以捕获中断请求
                const originalFetchApi = api.fetchApi;
                api.fetchApi = async function(url, options = {}) {
                    if (url === '/interrupt') {
                        api.dispatchEvent(new CustomEvent("execution_interrupt", { 
                            detail: { timestamp: Date.now() }
                        }));
                    }

                    return originalFetchApi.call(this, url, options);
                };
                
                // 中断请求监听器
                api.addEventListener("execution_interrupt", () => {
                    const senderNodes = app.graph._nodes.filter(n => 
                        n.type === "CCXGroupExecutorSender" && n.properties.isExecuting
                    );

                    senderNodes.forEach(node => {
                        if (node.properties.isExecuting && !node.properties.isCancelling) {
                            console.log(`[CCXGroupExecutorSender] 接收到中断请求，取消节点执行:`, node.id);
                            node.properties.isCancelling = true;
                            node.updateStatus("正在取消执行...");
                        }
                    });
                });
                
                // 前端执行模式的事件监听
                api.addEventListener("ccx_execute_group_list", async ({ detail }) => {
                    if (!detail || !detail.node_id || !Array.isArray(detail.execution_list)) {
                        console.error('[CCXGroupExecutorSender] 收到无效的执行数据:', detail);
                        return;
                    }

                    const node = app.graph._nodes_by_id[detail.node_id];
                    if (!node) {
                        console.error(`[CCXGroupExecutorSender] 未找到节点: ${detail.node_id}`);
                        return;
                    }

                    // 修复：检查节点是否已经在执行中，如果是则直接返回，避免重复执行
                    if (node.properties.isExecuting) {
                        console.warn('[CCXGroupExecutorSender] 节点已经在执行中，拒绝重复执行请求');
                        return;
                    }

                    // 修复：检查全局执行锁，如果有其他执行请求正在处理，则拒绝此请求
                    if (globalExecutionLock) {
                        console.warn('[CCXGroupExecutorSender] 全局执行锁已锁定，拒绝重复执行请求');
                        app.ui.dialog.show('已有执行任务正在进行中，请等待当前任务完成后再重试');
                        return;
                    }

                    // 设置全局执行锁
                    globalExecutionLock = true;

                    try {
                        const executionList = detail.execution_list;
                        console.log(`[CCXGroupExecutorSender] 收到执行列表:`, executionList);

                        // 检查节点是否已经在执行中，如果是则直接返回，避免重复执行
                        if (node.properties.isExecuting) {
                            console.warn('[CCXGroupExecutorSender] 节点已经在执行中，拒绝重复执行请求');
                            return;
                        }

                        node.properties.isExecuting = true;
                        node.properties.isCancelling = false;

                        // 计算执行项数量，考虑重复次数，以便生成正确的JOB序号
                        let totalTasks = executionList.reduce((total, item) => {
                            if (item.group_name !== "__delay__" && item.group_name) {
                                return total + (parseInt(item.repeat_count) || 1);
                            }
                            return total;
                        }, 0);
                        let currentTask = 0;

                        try {
                            for (const execution of executionList) {
                                if (node.properties.isCancelling) {
                                    console.log('[CCXGroupExecutorSender] 执行被取消');
                                    break;
                                }
                                
                                const group_name = execution.group_name || '';
                                const repeat_count = parseInt(execution.repeat_count) || 1;
                                const delay_seconds = parseFloat(execution.delay_seconds) || 0;

                                if (!group_name) {
                                    console.warn('[CCXGroupExecutorSender] 跳过无效的组名称:', execution);
                                    continue;
                                }

                                if (group_name === "__delay__") {
                                    if (delay_seconds > 0 && !node.properties.isCancelling) {
                                        node.updateStatus(
                                            `等待下一组 ${delay_seconds}s...`
                                        );
                                        await new Promise(resolve => setTimeout(resolve, delay_seconds * 1000));
                                    }
                                    continue;
                                }

                                // 为每次重复执行生成一个唯一的JOB类目标签
                                for (let repeat_index = 0; repeat_index < repeat_count; repeat_index++) {
                                    if (node.properties.isCancelling) {
                                        console.log('[CCXGroupExecutorSender] 执行被取消');
                                        break;
                                    }
                                    
                                    currentTask++;
                                    const progress = (currentTask / totalTasks) * 100;
                                    // 使用更清晰的任务标识，避免与后端Job编号混淆
                                    node.updateStatus(
                                        `执行组: ${group_name} (${currentTask}/${totalTasks})`,
                                        progress
                                    );
                                    
                                    try {
                                        const outputNodes = node.getGroupOutputNodes(group_name);
                                        if (!outputNodes || !outputNodes.length) {
                                            throw new Error(`组 "${group_name}" 中没有找到输出节点`);
                                        }

                                        const nodeIds = outputNodes.map(n => n.id);
                                        
                                        try {
                                            if (node.properties.isCancelling) {
                                                break;
                                            }
                                            await queueManager.queueOutputNodes(nodeIds);
                                            await node.waitForQueue();
                                        } catch (queueError) {
                                            if (node.properties.isCancelling) {
                                                break;
                                            }
                                            console.warn(`[CCXGroupExecutorSender] 队列执行失败，使用默认方式:`, queueError);
                                            for (const n of outputNodes) {
                                                if (node.properties.isCancelling) {
                                                    break;
                                                }
                                                if (n.triggerQueue) {
                                                    await n.triggerQueue();
                                                    await node.waitForQueue();
                                                }
                                            }
                                        }

                                        if (delay_seconds > 0 && (repeat_index < repeat_count - 1 || currentTask < totalTasks) && !node.properties.isCancelling) {
                                            node.updateStatus(
                                                `执行组: ${group_name} (${currentTask}/${totalTasks}) - 等待 ${delay_seconds}s`,
                                                progress
                                            );
                                            await new Promise(resolve => setTimeout(resolve, delay_seconds * 1000));
                                        }
                                    } catch (error) {
                                        throw new Error(`执行组 "${group_name}" 失败: ${error.message}`);
                                    }
                                }
                                
                                if (node.properties.isCancelling) {
                                    break;
                                }
                            }

                            if (node.properties.isCancelling) {
                                node.updateStatus("已取消");
                                setTimeout(() => node.resetStatus(), 2000);
                            } else {
                                node.updateStatus(`执行完成 (${totalTasks}/${totalTasks})`, 100);
                                setTimeout(() => node.resetStatus(), 2000);
                            }

                        } catch (error) {
                            console.error('[CCXGroupExecutorSender] 执行错误:', error);
                            node.updateStatus(`错误: ${error.message}`);
                            app.ui.dialog.show(`执行错误: ${error.message}`);
                        } finally {
                            node.properties.isExecuting = false;
                            node.properties.isCancelling = false;
                        }

                    } catch (error) {
                        console.error(`[CCXGroupExecutorSender] 执行失败:`, error);
                        app.ui.dialog.show(`执行错误: ${error.message}`);
                        node.updateStatus(`错误: ${error.message}`);
                        node.properties.isExecuting = false;
                        node.properties.isCancelling = false;
                    } finally {
                        // 释放全局执行锁
                        globalExecutionLock = false;
                        console.log('[CCXGroupExecutorSender] 全局执行锁已释放');
                    }
                });
                
                // 后台执行模式的事件监听
                api.addEventListener("ccx_execute_group_list_backend", async ({ detail }) => {
                    if (!detail || !detail.node_id || !Array.isArray(detail.execution_list)) {
                        console.error('[CCXGroupExecutorSender] 收到无效的后台执行数据:', detail);
                        return;
                    }
                    
                    const node = app.graph._nodes_by_id[detail.node_id];
                    if (!node) {
                        console.error(`[CCXGroupExecutorSender] 未找到节点: ${detail.node_id}`);
                        return;
                    }

                    // 修复：检查全局执行锁，如果有其他执行请求正在处理，则拒绝此请求
                    if (globalExecutionLock) {
                        console.warn('[CCXGroupExecutorSender] 全局执行锁已锁定，拒绝重复执行请求');
                        app.ui.dialog.show('已有执行任务正在进行中，请等待当前任务完成后再重试');
                        return;
                    }

                    // 设置全局执行锁
                    globalExecutionLock = true;
                    
                    try {
                        console.log(`[CCXGroupExecutorSender] 收到后台执行请求:`, detail.execution_list);
                        await node.executeInBackend(detail.execution_list);
                    } catch (error) {
                        console.error(`[CCXGroupExecutorSender] 后台执行失败:`, error);
                        app.ui.dialog.show(`执行错误: ${error.message}`);
                        if (node.updateStatus) {
                            node.updateStatus(`错误: ${error.message}`);
                        }
                    } finally {
                        // 释放全局执行锁
                        globalExecutionLock = false;
                        console.log('[CCXGroupExecutorSender] 全局执行锁已释放');
                    }
                });
                
                // 标记所有事件监听器已注册
                eventListenersRegistered = true;
                console.log(`[CCXGroupExecutorSender] 所有事件监听器已注册`);
            }
        }
    }
});

