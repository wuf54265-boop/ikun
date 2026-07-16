"""Step 7 端到端冒烟（不依赖真实 OpenAI API）。

通过 monkeypatch 验证：
1. 无 API key -> /insight/report 返回 503
2. LLM 正常返回 -> 服务透传四字段
3. LLM 抛错(LLMError) -> 降级为结构化摘要
4. /insight/report/stream -> SSE 格式 + 文本逐块 + [DONE]
5. llm._normalize 容错（```json 围栏 / 脏输出）
"""
import sys
import types
from unittest.mock import patch

# 不触发 lifespan 建库，直接用 TestClient 的 with 上下文
from fastapi.testclient import TestClient

import app.ai.llm as llm_mod
import app.services.insight as svc
from app.main import app


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f"  ({detail})" if detail else ""))
    if not cond:
        global FAILED
        FAILED += 1


FAILED = 0


def _fake_settings(key: str):
    s = types.SimpleNamespace()
    s.openai_api_key = key
    s.openai_model = "gpt-4o-mini"
    return s


def test_no_key_503():
    with patch("app.routers.insight.get_settings", return_value=_fake_settings("")):
        with TestClient(app) as client:
            r = client.post("/api/v1/insight/report", json={"results": [], "tone": "professional"})
    check("无 key -> 503", r.status_code == 503, f"code={r.status_code}")
    check("503 提示含 OPENAI_API_KEY", "OPENAI_API_KEY" in r.text, r.text[:80])


def test_normal_translate():
    fake = {
        "summary": "摘要文本",
        "key_findings": ["[回归分析] 系数显著"],
        "suggestions": ["建议A"],
        "risks": ["风险B"],
    }
    with patch.object(llm_mod.LLMClient, "generate_report", return_value=fake):
        data = svc.generate_report(_req())
    check("正常翻译 summary", data.summary == "摘要文本")
    check("正常翻译 key_findings", data.key_findings == ["[回归分析] 系数显著"])
    check("正常翻译 suggestions", data.suggestions == ["建议A"])
    check("正常翻译 risks", data.risks == ["风险B"])


def test_degraded_on_llm_error():
    def boom(self, sr, tone="professional"):
        raise llm_mod.LLMError("boom")

    with patch.object(llm_mod.LLMClient, "generate_report", boom):
        data = svc.generate_report(_req())
    check("降级 summary 含 结构化分析摘要", "结构化分析摘要" in data.summary)
    check("降级 key_findings 来自 explanation", any("来源" in f for f in data.key_findings), str(data.key_findings))
    check("降级 suggestions 为空", data.suggestions == [])


def test_stream_sse():
    async def fake_stream(self, sr, tone="professional"):
        for tok in ["数据", "分析", "完成"]:
            yield tok

    with patch("app.routers.insight.get_settings", return_value=_fake_settings("sk-test")):
        with patch.object(llm_mod.LLMClient, "generate_report_stream", fake_stream):
            with TestClient(app) as client:
                r = client.post(
                    "/api/v1/insight/report/stream",
                    json={"results": _req().results, "tone": "professional"},
                )
    body = r.text
    check("流式 200", r.status_code == 200, f"code={r.status_code}")
    check("流式 Content-Type SSE", "text/event-stream" in r.headers.get("content-type", ""))
    check("流式含 data: 事件", "data:" in body)
    check("流式含 [DONE]", "[DONE]" in body)
    check("流式逐块输出文本", '"数据"' in body and '"分析"' in body and '"完成"' in body)


def test_normalize_robust():
    fenced = llm_mod._normalize('```json\n{"summary":"S","key_findings":["a"],"suggestions":[],"risks":[]}\n```')
    check("围栏 JSON 解析", fenced["summary"] == "S" and fenced["key_findings"] == ["a"])
    dirty = llm_mod._normalize('瞎说 {"summary": "X", "key_findings": ["[回归分析] y"]}')
    check("脏输出兜底解析", dirty["summary"] == "X" and "[回归分析] y" in dirty["key_findings"])


def _req():
    from app.schemas.insight import InsightRequest

    return InsightRequest(
        results=[
            {
                "module": "回归分析",
                "data": {"r_squared": 0.9},
                "explanation": {"interpretation": "来源：回归 R²=0.9"},
            }
        ],
        tone="professional",
    )


if __name__ == "__main__":
    test_no_key_503()
    test_normal_translate()
    test_degraded_on_llm_error()
    test_stream_sse()
    test_normalize_robust()
    print(f"\n{'='*40}\n结果：{'全部通过' if FAILED == 0 else f'{FAILED} 项失败'}")
    sys.exit(1 if FAILED else 0)
