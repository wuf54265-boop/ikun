# Step 7: AI 分析报告生成

实现 **LLM 驱动的自然语言分析报告生成**。核心原则：LLM 只做"翻译"——所有数字来自前序结构化计算结果，绝不凭空编造。

## 已有基础设施

```
AI 层：
├── ai/llm.py              # LLMClient 骨架（__init__ 已有，generate_report 待实现）
├── services/insight.py    # generate_report() 骨架
├── routers/insight.py     # POST /insight/report（骨架）
├── schemas/insight.py     # InsightRequest / InsightData（已完整）

前端：
├── app/dataset/[id]/report/page.tsx  # 占位页（本次重写）
└── store/useAnalysisStore.ts         # results 字典（前序各步分析结果）
```

---

## 第一部分：LLM 客户端（ai/llm.py）

### 设计原则

1. **LLM 不做计算**：prompt 中强制要求"你是一个数据分析报告翻译器，所有数字必须来自下方提供的计算结果，不得编造任何统计量、百分比、具体数值"
2. **结构化注入**：将前序模块的 `data` + `explanation` 组装成结构化 JSON 注入 prompt
3. **支持流式输出**（`stream=True`）：供前端打字机效果

### 实现

```python
class LLMClient:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        # 已有，不重写

    def generate_report(self, structured_results: list[dict], tone: str = "professional") -> dict:
        """非流式，返回 {summary, key_findings, suggestions, risks}"""
        # 组装 prompt → 调 OpenAI → 解析返回

    async def generate_report_stream(self, structured_results: list[dict], tone: str = "professional"):
        """流式生成器，逐 chunk yield 文本片段"""
```

### System Prompt 设计（核心）

```
你是一位资深数据分析师。请将下方提供的结构化分析结果"翻译"成中文分析报告。
严格规则：
1. 所有数字（百分比、均值、p值、R²、系数等）必须来自下方数据，不得编造任何具体数值
2. 每个结论后标注数据来源（如[相关性分析]、[回归分析]）
3. 使用{ tone }语气
4. 输出 JSON 格式：{"summary": "...", "key_findings": ["...", ...], "suggestions": ["...", ...], "risks": ["...", ...]}

数据集背景：{rows}行 × {cols}列
分析结果：
{json.dumps(structured_results, ensure_ascii=False)}
```

### 要点
- User prompt 中注入 `rows`、`cols` 等上下文
- 要求 JSON 输出以便解析；加 fallback：如果 LLM 返回非 JSON，用正则提取四个字段
- 若 `OPENAI_API_KEY` 为空，返回明确的错误提示而非崩溃
- API 调用失败时返回降级报告："LLM 服务暂时不可用，以下是结构化分析摘要"

---

## 第二部分：报告服务（services/insight.py）

### generate_report(body: InsightRequest)

1. 从 `body.results` 提取各模块的 `data` 和 `explanation`
2. 为 prompt 补充数据集上下文（rows/cols，从第一个 result 中提取或用 body 传入）
3. 调用 `LLMClient.generate_report()`
4. 解析返回 JSON 并组装 `InsightData`
5. 验证：每个 key_finding 是否至少关联一个数据源（无则降级）

### generate_report_stream(body: InsightRequest)

- 异步生成器，流式返回报告段落
- 以 SSE 格式或简单 text/plain 流式输出
- 前端收到完整 JSON 后关闭流

---

## 第三部分：路由（routers/insight.py）

### POST /insight/report

- 调用 `services.insight.generate_report(body)`
- 返回 `AnalysisResponse[InsightData]`
- explanation 中写明："LLM 仅翻译结构化结果，所有数字来自前序统计计算"

### POST /insight/report/stream

- 流式端点，`StreamingResponse`
- Content-Type: `text/event-stream`
- 逐步输出报告 JSON 的构建过程（每个 key 输出一次更新）

如果 OpenAI API key 未配置，返回 503 并提示设置 `OPENAI_API_KEY`。

---

## 第四部分：前端报告页

重写 `frontend/app/dataset/[id]/report/page.tsx`：

### 报告配置区
- 语气选择：专业 / 通俗
- 勾选要包含的分析模块（概览/清洗/统计/建模，默认全选）
- "生成报告"按钮

### 报告展示区
- **流式输出**：打字机效果逐段显示（用 EventSource 或 fetch + ReadableStream）
- **Markdown 渲染**：summary 用 Markdown 显示（可引入 react-markdown 或简单的 Markdown 转 HTML 工具函数）
- **四个板块**：摘要、关键发现（编号列表）、建议（编号列表）、风险提示
- 每个发现旁标注数据来源标签（如 `[相关性分析]` `[回归分析]`）

### 可溯源设计
- 每个 key_finding 如果是来自特定分析模块，用不同颜色标签区分
- 点击标签跳转到对应分析页（`/dataset/[id]/stats` 等）

### 降级处理
- LLM 调用失败 → 展示"结构化分析摘要"（用前序各步的 explanation.interpretation 拼成纯文本报告）
- API key 未配置 → 展示设置引导

### 前端新增包
- 如需 Markdown 渲染，在 `package.json` 中添加 `react-markdown`

---

## 第五部分：测试

不需要自动化测试（依赖外部 API），但需要：

- 在 `backend/tests/step07_manual.md` 中写一份手动验证说明：
  - 如何设置 `OPENAI_API_KEY`
  - curl 命令验证 `/insight/report`
  - 期望返回值格式
  - 降级行为验证（不设 key 时的 503 响应）

---

## 需要输出的文件清单

### 后端
1. `backend/app/ai/llm.py` — 完整实现 generate_report() + generate_report_stream()
2. `backend/app/services/insight.py` — 完整实现 generate_report() + 流式版
3. `backend/app/routers/insight.py` — 重写，连接 service
4. `backend/app/schemas/insight.py` — 补 dataset_context 字段（rows/cols）

### 前端
5. `frontend/app/dataset/[id]/report/page.tsx` — 重写完整报告页
6. `frontend/package.json` — 如需加 react-markdown

### 文档
7. `backend/tests/step07_manual.md` — 手动验证说明

---

## 验证清单

- [ ] OpenAI API key 配置正确时，POST /insight/report 返回 200
- [ ] 报告包含 summary / key_findings / suggestions / risks 四个字段
- [ ] 报告中的数字来自结构化结果（人工抽查 1-2 个数值）
- [ ] 未配置 API key 时返回 503
- [ ] 前端报告页正常渲染，支持语气切换
- [ ] 流式端点输出 SSE 格式（可选，P1）

---

**核心约束：LLM 必须是"翻译器"而非"算命师"。System prompt 必须强制所有数字来自注入数据，禁止编造。**
