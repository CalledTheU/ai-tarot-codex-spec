# AI 工作流与 RAG 规格

## 工作流
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
