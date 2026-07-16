"""LLM 客户端封装（OpenAI）。

职责：把结构化结果「翻译」成自然语言报告。所有数字来自传入的结构化数据，
不得让模型自由编造统计量（system prompt 中强制约束）。
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import AsyncIterator

from openai import OpenAI

# 模型调用失败时抛出，供上层降级为「结构化分析摘要」
class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, api_key: str, model: str):
        # 保留原始 key 用于空值检测；OpenAI 不允许空字符串，用占位符避免构造即崩溃
        self.api_key = api_key
        self.model = model
        self.client = OpenAI(api_key=api_key or "sk-no-key")

    # ------------------------------------------------------------------
    # Prompt 组装
    # ------------------------------------------------------------------
    def _messages(self, structured_results: list[dict], tone: str) -> list[dict]:
        """组装 system + user 消息。rows/cols 从背景项中提取。"""
        # 从结构化结果里找「数据集背景」项，提取行/列数
        rows = cols = "未知"
        for item in structured_results:
            if item.get("module") == "数据集背景":
                d = item.get("data", {}) or {}
                rows = d.get("rows", "未知")
                cols = d.get("cols", "未知")
                break

        system = (
            "你是一位资深数据分析师。请将下方提供的结构化分析结果“翻译”成中文分析报告。\n"
            "严格规则：\n"
            "1. 所有数字（百分比、均值、p值、R²、系数、轮廓系数等）必须来自下方数据，"
            "不得编造任何具体数值；若数据中没有对应数值，不要凭空给出。\n"
            "2. 每个结论后标注数据来源（如[相关性分析]、[回归分析]、[数据清洗]、[数据概览]），"
            "方便读者回溯。\n"
            f"3. 使用{tone}语气。\n"
            "4. 仅输出 JSON，不要任何额外说明，格式：\n"
            '{"summary": "...", "key_findings": ["...", "..."], '
            '"suggestions": ["...", "..."], "risks": ["...", "..."]}'
        )
        user = (
            f"数据集背景：{rows} 行 × {cols} 列\n"
            "以下是前序各分析模块的结构化计算结果（data 为统计量，explanation 为解读）：\n"
            + json.dumps(structured_results, ensure_ascii=False, default=str)
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    # ------------------------------------------------------------------
    # 非流式：返回 {summary, key_findings, suggestions, risks}
    # ------------------------------------------------------------------
    def generate_report(
        self, structured_results: list[dict], tone: str = "professional"
    ) -> dict:
        """调用 LLM 生成报告 dict。LLM 只翻译，不计算。"""
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY 未配置，无法调用 LLM。")
        messages = self._messages(structured_results, tone)
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or "{}"
        except Exception as e:  # noqa: BLE001 - 任何调用异常都降级
            raise LLMError(f"LLM 调用失败：{e}") from e
        return _normalize(content)

    # ------------------------------------------------------------------
    # 流式：逐 chunk yield 文本片段（供前端打字机）
    # ------------------------------------------------------------------
    async def generate_report_stream(
        self, structured_results: list[dict], tone: str = "professional"
    ) -> AsyncIterator[str]:
        """异步生成器，逐 chunk yield 文本片段。

        用同步 OpenAI 客户端的 stream=True 迭代器，但把每次 next() 放到线程池，
        避免阻塞 FastAPI 事件循环。
        """
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY 未配置，无法调用 LLM。")
        messages = self._messages(structured_results, tone)
        loop = asyncio.get_event_loop()
        try:
            def _create_stream():
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    stream=True,
                )

            stream = await loop.run_in_executor(None, _create_stream)
            while True:
                try:
                    chunk = await loop.run_in_executor(None, next, stream)
                except StopIteration:
                    break
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:  # noqa: BLE001
            raise LLMError(f"LLM 流式调用失败：{e}") from e


# ----------------------------------------------------------------------
# 解析与归一化
# ----------------------------------------------------------------------
def _as_list(v) -> list[str]:
    if isinstance(v, list):
        return [str(x) for x in v]
    if v is None or v == "":
        return []
    return [str(v)]


def _normalize(content: str) -> dict:
    """解析模型输出为四字段 dict；兼容 ```json 围栏与脏输出。"""
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()

    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        obj = _extract_fallback(text)

    return {
        "summary": str(obj.get("summary", "")),
        "key_findings": _as_list(obj.get("key_findings")),
        "suggestions": _as_list(obj.get("suggestions")),
        "risks": _as_list(obj.get("risks")),
    }


def _extract_fallback(text: str) -> dict:
    """JSON 解析失败时的兜底：先截取首 { 到末 } 再尝试解析；仍失败则用正则。"""
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    obj: dict = {"summary": "", "key_findings": [], "suggestions": [], "risks": []}
    for key in ("summary", "key_findings", "suggestions", "risks"):
        m = re.search(rf'"?{key}"?\s*:\s*(.+)', text, re.IGNORECASE)
        if not m:
            continue
        raw = m.group(1).rstrip(" ,").strip()
        if key == "summary":
            obj["summary"] = raw.strip().strip('"')
        else:
            arr = re.findall(r'"([^"]*)"', raw)
            if arr:
                obj[key] = arr
    return obj
