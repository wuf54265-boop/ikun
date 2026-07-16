"""数据集接入：上传 / 列表 / 元数据 / 内置示例。"""
import json

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.config import get_settings
from app.dependencies import get_dataset_repo
from app.schemas.common import AnalysisResponse, Explanation, Meta
from app.schemas.dataset import ColumnInfo, UploadResponse
from app.services import ingestion
from app.store.dataset_repo import DatasetRepository

router = APIRouter(tags=["datasets"])

MAX_MB = get_settings().max_upload_mb


@router.post("/datasets/upload", response_model=AnalysisResponse[UploadResponse])
async def upload(
    file: UploadFile = File(...),
    repo: DatasetRepository = Depends(get_dataset_repo),
):
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="空文件：未读取到任何字节")

    size_mb = len(raw) / (1024 * 1024)
    if size_mb > MAX_MB:
        raise HTTPException(
            status_code=413,
            detail=f"文件 {size_mb:.1f}MB 超过上限 {MAX_MB}MB",
        )

    try:
        result = await ingestion.ingest(raw, file.filename or "unknown.csv", repo)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # 解析/落盘意外错误
        raise HTTPException(status_code=422, detail=f"解析失败：{e}")

    return AnalysisResponse(
        data=result,
        explanation=Explanation(
            method="read_table_file 解析 + 列类型推断 + Parquet 落盘",
            interpretation=result.note or "已完成解析与落盘，可进入数据概览。",
            assumptions=["编码探测顺序 utf-8 → gbk → gb2312 → gb18030 → latin-1"],
        ),
        meta={
            "dataset_id": result.dataset_id,
            "rows": result.rows,
            "cols": result.cols,
        },
    )


@router.get("/datasets", response_model=list)
def list_datasets(repo: DatasetRepository = Depends(get_dataset_repo)):
    return repo.list_datasets()


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str, repo: DatasetRepository = Depends(get_dataset_repo)):
    meta = repo.get_metadata(dataset_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="dataset not found")
    return meta


def _make_demo_df(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """生成可复现的内置电商示例数据（seed=42）。

    列：customer_id / order_date / amount / quantity / category / is_member / channel
    - 约 120 个客户，使 RFM 分组有意义
    - 日期分布于最近 180 天内，便于 RFM 的 R 计算
    """
    rng = np.random.default_rng(seed)
    n_customers = 120
    today = pd.Timestamp.now().normalize()
    customer_ids = [f"C{ i:04d}" for i in range(1, n_customers + 1)]

    rows = rng.integers(0, n_customers, size=n)
    date_offsets = rng.integers(0, 180, size=n)
    order_dates = [today - pd.Timedelta(days=int(d)) for d in date_offsets]

    amounts = np.round(rng.lognormal(mean=4.0, sigma=0.6, size=n), 2)
    quantities = rng.integers(1, 6, size=n)
    categories = rng.choice(["食品", "服饰", "数码", "家居", "美妆"], size=n)
    is_member = rng.random(size=n) < 0.4
    channels = rng.choice(["app", "web", "门店", "小程序"], size=n)

    return pd.DataFrame(
        {
            "customer_id": [customer_ids[i] for i in rows],
            "order_date": order_dates,
            "amount": amounts,
            "quantity": quantities,
            "category": categories,
            "is_member": is_member,
            "channel": channels,
        }
    )


def _infer_type(series: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    return "categorical"


@router.post("/datasets/demo", response_model=AnalysisResponse[UploadResponse])
def create_demo(repo: DatasetRepository = Depends(get_dataset_repo)):
    """创建内置电商示例数据集（seed=42 可复现），返回 dataset_id 供前端一键体验。"""
    df = _make_demo_df()
    dataset_id = repo.save_raw(df, "demo_ecommerce.csv")

    preview = json.loads(df.head(20).to_json(orient="records", date_format="iso"))
    columns = [
        ColumnInfo(
            name=col,
            inferred_type=_infer_type(df[col]),
            confidence=1.0,
            sample_values=json.loads(df[col].head(3).to_json(orient="values", date_format="iso")),
        )
        for col in df.columns
    ]

    return AnalysisResponse(
        data=UploadResponse(
            dataset_id=dataset_id,
            filename="demo_ecommerce.csv",
            rows=int(df.shape[0]),
            cols=int(df.shape[1]),
            columns=columns,
            preview=preview,
            note="内置电商示例数据（NumPy seed=42 可复现），含 7 列，可直接体验 RFM / 漏斗模板。",
        ),
        explanation=Explanation(
            method="内置示例数据生成（NumPy seed=42）",
            interpretation="约 500 行电商交易数据：customer_id / order_date / amount / quantity / category / is_member / channel。",
            assumptions=["随机生成但固定 seed，结果可复现", "日期相对生成当天，最近 180 天内"],
        ),
        meta=Meta(
            method="demo_dataset",
            params={"rows": int(df.shape[0]), "cols": int(df.shape[1]), "seed": 42},
        ),
    )
