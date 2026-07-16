# Step 7 手动验证说明（AI 分析报告）

> Step 7 依赖外部 OpenAI API，无自动化测试。本文件说明如何手动验证
> `POST /api/v1/insight/report` 与流式端点 `/api/v1/insight/report/stream`。

---

## 1. 配置 OPENAI_API_KEY

复制 `.env.example` 为 `.env` 并填写真实 key：

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env
# OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
# OPENAI_MODEL=gpt-4o-mini
```

环境变量由 `pydantic-settings` 在 `app/config.py` 读取（无需改代码）。
前端通过 `.env.local` 的 `NEXT_PUBLIC_API_BASE` 指向后端（默认 `http://localhost:8000/api/v1`）。

---

## 2. 启动后端

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

---

## 3. 验证「无 key 返回 503」

先把 `.env` 里的 `OPENAI_API_KEY` 清空（或临时设为空字符串），重启后端，然后：

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/v1/insight/report \
  -H "Content-Type: application/json" \
  -d '{"results":[],"tone":"professional"}'
# 期望：503
```

响应体类似：

```json
{ "detail": "OPENAI_API_KEY 未配置，请在 .env 中设置后重试。" }
```

前端表现：报告页顶部显示红色错误条，提示配置 `OPENAI_API_KEY`。

---

## 4. 验证「正常生成报告」（需有效 key）

`results` 为前序各模块的结构化结果数组，每项形如
`{ "module": "回归分析", "data": {...}, "explanation": {"interpretation": "..."} }`。

```bash
curl -s -X POST http://localhost:8000/api/v1/insight/report \
  -H "Content-Type: application/json" \
  -d '{
    "results": [
      {
        "module": "回归分析",
        "data": {"r_squared": 0.92, "coefficients": [{"name":"x1","coef":1.2,"p_value":0.01}]},
        "explanation": {"interpretation": "回归 R²=0.92，x1 显著（p=0.01）。"}
      }
    ],
    "tone": "professional",
    "dataset_context": {"rows": 1000, "cols": 12}
  }'
```

### 期望返回格式

```json
{
  "data": {
    "summary": "本报告基于 1000 行 × 12 列数据……",
    "key_findings": [
      "[回归分析] x1 对目标有显著正向影响（p=0.01，R²=0.92）"
    ],
    "suggestions": ["建议进一步……"],
    "risks": ["样本外泛化风险……"]
  },
  "explanation": "LLM 仅翻译结构化结果，所有数字来自前序统计计算，未做任何自由编造。",
  "meta": { "tone": "professional" }
}
```

### 抽查要点（核心约束）

- `key_findings` 中出现的数值（R²=0.92、p=0.01）必须来自请求 `results` 中的 `data`，
  LLM 不得编造未提供的统计量。
- 每个结论应带来源标签 `[回归分析]` 等，可前端点击跳转对应分析页。

---

## 5. 验证「降级」（key 有效但 API 调用失败）

当 OpenAI 调用抛错（如网络不通、额度耗尽）时，后端捕获 `LLMError`，
返回 **降级报告**：用各模块 `explanation.interpretation` 拼成纯文本摘要，
HTTP 仍为 200。前端显示琥珀色「LLM 服务暂不可用」提示条。

人工验证：临时把 `OPENAI_MODEL` 设为一个不存在的模型名，或断网，再发请求，
应得到一个 `summary` 以「LLM 服务暂时不可用，以下是结构化分析摘要：」开头的报告。

---

## 6. （P1）流式端点 SSE

```bash
curl -N -X POST http://localhost:8000/api/v1/insight/report/stream \
  -H "Content-Type: application/json" \
  -d '{"results":[{"module":"回归分析","data":{"r_squared":0.92},"explanation":{"interpretation":"R²=0.92"}}],"tone":"professional"}'
```

期望逐块输出 `text/event-stream`：

```
data: {"text": "本"}
data: {"text": "报告"}
...
event: done
data: [DONE]
```

前端 ReportView 在流式过程中用打字机效果渲染累积文本，流结束后把完整 JSON
解析为「摘要 / 关键发现 / 建议 / 风险」四板块。

---

## 7. 端到端冒烟（不依赖真实 API）

`backend/tests/step07_e2e.py` 通过 monkeypatch 覆盖：

- 无 key → 503
- LLM 正常 → 四字段透传
- LLM 报错 → 降级摘要
- 流式 → SSE 格式 + 逐块 + [DONE]
- `_normalize` 容错（```json 围栏 / 脏输出）

运行：

```bash
cd backend
python -m tests.step07_e2e
```
