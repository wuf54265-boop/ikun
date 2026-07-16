"""AI 报告服务：聚合结构化结果 -> 调 LLM 生成自然语言。

LLM 只做「翻译」：所有数字来自 body.results，不得编造。
"""
from __future__ import annotations

from typing import AsyncIterator

from app.ai.llm import LLMClient, LLMError
from app.config import get_settings
from app.schemas.insight import InsightData, InsightRequest


def _build_structured(results: list[dict], dataset_context: dict | None) -> list[dict]:
    """组装注入 LLM 的结构化结果：先放数据集背景项，再放各模块。"""
    items: list[dict] = []
    if dataset_context:
        items.append(
            {
                "module": "数据集背景",
                "data": {
                    "rows": dataset_context.get("rows"),
                    "cols": dataset_context.get("cols"),
                },
                "explanation": {
                    "interpretation": (
                        f"数据集共 {dataset_context.get('rows')} 行 × "
                        f"{dataset_context.get('cols')} 列。"
                    )
                },
            }
        )
    for r in results:
        items.append(
            {
                "module": r.get("module", "分析模块"),
                "data": r.get("data", r),
                "explanation": r.get("explanation", {}) or {},
            }
        )
    return items


def _degraded_report(results: list[dict]) -> InsightData:
    """LLM 不可用时的降级：用各模块 explanation.interpretation 拼成纯文本摘要。"""
    parts: list[str] = []
    findings: list[str] = []
    for r in results:
        mod = r.get("module", "分析模块")
        interp = (r.get("explanation") or {}).get("interpretation", "")
        if interp:
            parts.append(f"【{mod}】{interp}")
            findings.append(f"【{mod}】{interp}")
    summary = "LLM 服务暂时不可用，以下是结构化分析摘要：\n" + "\n".join(parts)
    return InsightData(summary=summary, key_findings=findings, suggestions=[], risks=[])


def generate_report(body: InsightRequest) -> InsightData:
    settings = get_settings()
    client = LLMClient(api_key=settings.openai_api_key, model=settings.openai_model)
    structured = _build_structured(body.results, body.dataset_context)
    try:
        rep = client.generate_report(structured, tone=body.tone)
    except LLMError:
        return _degraded_report(body.results)

    data = InsightData(
        summary=rep.get("summary", ""),
        key_findings=rep.get("key_findings", []) or [],
        suggestions=rep.get("suggestions", []) or [],
        risks=rep.get("risks", []) or [],
    )
    # 验证：关键发现为空 -> 视为 LLM 未产出有效内容，降级
    if not data.key_findings:
        return _degraded_report(body.results)
    return data


async def generate_report_stream(body: InsightRequest) -> AsyncIterator[str]:
    """异步生成器，逐 chunk yield 文本片段（供 SSE）。"""
    settings = get_settings()
    client = LLMClient(api_key=settings.openai_api_key, model=settings.openai_model)
    structured = _build_structured(body.results, body.dataset_context)
    async for chunk in client.generate_report_stream(structured, tone=body.tone):
        yield chunk
