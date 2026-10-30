# AI 工作流与 RAG 规格

## 当前实现：Phase 4

尚未使用 LangGraph、向量检索或自动修复。当前顺序是：所有者鉴权 → 读取不可变快照 → 提交 processing/run_id → 构建独立系统提示与不可信 JSON 上下文 → 一次模型调用 → Pydantic + 牌面/来源校验 → 保存完成或失败。数据库事务不跨越 HTTP 调用。`backend/app/services/interpretation.py` 实现业务，`backend/app/llm.py` 实现可替换适配器和 OpenAI 兼容客户端。

提示词版本为 `basic-interpretation-v1`。只有快照中抽到的牌、对应方向的历史摘录及其来源编号提供给模型，背景与资料不能覆盖系统规则。traditional_meaning 必须精确复制原英文摘录；contextual_interpretation 与 possible_scenarios 是生成解释与推演。输出校验不能保证内容事实性或安全语义；真实模型质量与高风险问题人工评估尚未完成。

`LLM_PROVIDER=openai_compatible`，实际服务的 `LLM_BASE_URL`（通常含 `/v1`）与 `LLM_MODEL` 必填于调用时；密钥可选。HTTPX 禁止重定向、不读取系统代理，设置超时和输出 token 上限；兼容服务须接受 `response_format=json_object`。HTTP 响应上限 256 KiB，生成文本上限 64000 字符；截断、工具调用式空内容、供应商错误均失败。没有模型时抽牌独立可用。

每个请求最多调用一次，失败需用户显式重试；Phase 5 再实现最多一次修复。成功结果缓存于原记录。processing 超过 timeout + 30 秒可重新领取；active_run_id 保证过期请求无法覆盖新结果。AgentRun 仅存模型/版本/耗时/允许的 token 计数和安全错误码，retry_count=0 表示本请求无自动重试；显式重试产生新运行行。不会保存完整提示、用户背景、原始模型响应或异常详情。

Phase 4 采用 mock 验证超时、失败后成功、无效 JSON、虚构牌/牌位/方向/来源、并发和快照一致性；不代表 Qwen3-0.6B 已安装、兼容性或质量已实测。

## 后续 LangGraph 工作流（Phase 5–6）
`load_context → retrieve_knowledge → build_context → generate_interpretation → validate_interpretation → [repair once] → persist_result`

任何节点失败必须进入可解释的错误分支。数据库事务不跨越外部模型调用。

## State
至少包含：
- reading_id
- question/category/background
- spread snapshot
- cards snapshot
- knowledge_chunks
- draft
- validation_errors
- repair_count
- final_result
- error_code

## 节点约束
- load_context：校验用户对 Reading 的访问权，加载持久化快照。
- retrieve_knowledge：先使用 card_id、orientation 等结构化过滤，再按需执行全文/向量检索。
- build_context：限制总上下文长度；将检索内容标为不可信资料。
- generate_interpretation：调用模型适配器并要求严格 JSON。
- validate_interpretation：检查 Schema、牌面 ID、牌位索引/名称、正逆位、每个牌位恰好一次、来源 ID。
- repair：最多一次，只传校验错误和必要输入。
- persist_result：仅保存通过校验的结果；失败时保存安全错误码。

## 牌义来源
每个来源记录 title、source_id、source URL/书目信息、license、version、content_hash。不得将没有许可的内容加入可分发种子数据。

## 检索策略
- 牌面已知时，直接读取牌库中的结构化正/逆位解释。
- 补充知识使用 PostgreSQL 全文检索和 pgvector；可根据评估决定是否融合排序。
- 结果去重并限制 top_k 和 token 预算。
- 模型只能引用本次检索返回的 source_id。
- RAG 关闭时仍可基于结构化牌义生成基础解读。

## 安全
- Prompt injection 文本不具有系统指令优先级。
- 不执行模型输出中的工具调用、SQL、Shell 或文件路径。
- 不推断用户或第三方未提供的事实。
- 不将塔罗作为医学、法律、投资结论。
- 不记录密钥、Cookie、密码或不必要的完整敏感背景。

## 评估
维护至少 30 条人工审核用例，覆盖主题、牌阵、正逆位、冲突牌义、无关检索内容、模型超时、无效 JSON 和伪造引用。报告召回、来源有效率、牌位一致率、Schema 通过率、延迟和人工质量评分。
