"""AI 分析报告：结构化结果 -> 自然语言（LLM 只做翻译）。"""
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.schemas.common import AnalysisResponse
from app.schemas.insight import InsightData, InsightRequest
from app.services import insight as insight_svc

router = APIRouter(prefix="/insight", tags=["insight"])


@router.post("/report", response_model=AnalysisResponse[InsightData])
def report(body: InsightRequest):
    settings = get_settings()
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503, detail="OPENAI_API_KEY 未配置，请在 .env 中设置后重试。"
        )
    data = insight_svc.generate_report(body)
    return AnalysisResponse(
        data=data,
        explanation={
            "method": "LLM 结构化翻译（OpenAI）",
            "assumptions": [
                "LLM 仅翻译结构化计算结果，所有数字来自前序统计模块",
                "不编造任何统计量、百分比或具体数值",
            ],
            "interpretation": "自然语言报告已生成，每个关键发现标注了数据来源（[相关性分析]等），可点击回溯。",
            "caveats": [
                "LLM 对专业术语的理解可能存在偏差",
                "报告结论应结合原始数据与业务背景综合判断",
            ],
        },
        meta={"method": "llm_report", "params": {"tone": body.tone, "modules": len(body.results)}},
    )


@router.post("/report/stream")
async def report_stream(body: InsightRequest):
    """流式报告：text/event-stream，逐 chunk 推送 SSE 事件。"""
    settings = get_settings()
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503, detail="OPENAI_API_KEY 未配置，请在 .env 中设置后重试。"
        )

    async def event_gen():
        async for chunk in insight_svc.generate_report_stream(body):
            yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
