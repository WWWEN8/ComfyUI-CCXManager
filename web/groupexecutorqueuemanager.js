import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "GroupExecutorQueueManager",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (api.fetchApi._isGroupExecutorQueueManager) {
            return;
        }

        const originalFetchApi = api.fetchApi;

        function collectRelatedNodes(prompt, nodeId, relevantNodes) {
            if (!prompt[nodeId] || relevantNodes.has(nodeId)) return;
            relevantNodes.add(nodeId);

            const node = prompt[nodeId];
            if (node.inputs) {
                Object.values(node.inputs).forEach(input => {
                    if (input && input.length > 0) {
                        collectRelatedNodes(prompt, input[0], relevantNodes);
                    }
                });
            }
        }

        const newFetchApi = async function(url, options = {}) {

            if (url === '/prompt' && options.method === 'POST') {
                const requestData = JSON.parse(options.body);

                if (requestData.extra_data?.isGroupExecutorRequest) {
                    return originalFetchApi.call(api, url, options);
                }

                const prompt = requestData.prompt;

                // 修改：检查 CCXGroupExecutorSender 而不是旧的 GroupExecutorSender
                const hasGroupExecutor = Object.values(prompt).some(node => 
                    node.class_type === "CCXGroupExecutorSender"
                );

                if (hasGroupExecutor) {

                    const relevantNodes = new Set();
                    
                    for (const [nodeId, node] of Object.entries(prompt)) {
                        // 修改：查找 CCXGroupExecutorSender 节点
                        if (node.class_type === "CCXGroupExecutorSender") {
                            collectRelatedNodes(prompt, nodeId, relevantNodes);
                        }
                    }

                    const filteredPrompt = {};
                    for (const nodeId of relevantNodes) {
                        if (prompt[nodeId]) {
                            filteredPrompt[nodeId] = prompt[nodeId];
                        }
                    }

                    const modifiedOptions = {
                        ...options,
                        body: JSON.stringify({
                            ...requestData,
                            prompt: filteredPrompt,
                            extra_data: {
                                ...requestData.extra_data,
                                isGroupExecutorRequest: true
                            }
                        })
                    };

                    return originalFetchApi.call(api, url, modifiedOptions);
                }
            }

            return originalFetchApi.call(api, url, options);
        };

        newFetchApi._isGroupExecutorQueueManager = true;

        api.fetchApi = newFetchApi;
    }
});