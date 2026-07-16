"""接入服务：解析上传文件 -> 类型推断 -> 采样 -> 落盘 Parquet -> 预览。

流程：
1. read_table_file 解析字节流为 DataFrame（编码探测链在 utils.io）
2. 行数 > settings.sample_rows 时随机采样，类型推断/预览只基于样本，保证 <10s
3. 全量 DataFrame 落盘 Parquet（repo.save_raw），采样不影响原始数据
4. 逐列类型推断 + 前 20 行预览，组装 UploadResponse
"""
from __future__ import annotations

from typing import Any

import math

import numpy as np
import pandas as pd

from app.config import get_settings
from app.schemas.dataset import ColumnInfo, UploadResponse
from app.store.dataset_repo import DatasetRepository
from app.utils.column_types import infer_column_type
from app.utils.io import read_table_file

PREVIEW_ROWS = 20


def _to_jsonable(obj: Any) -> Any:
    """把 numpy / pandas 标量转成 JSON 安全类型，NaN/NaT -> None。"""
    if obj is None:
        return None
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        f = float(obj)
        return None if math.isnan(f) or math.isinf(f) else f
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return obj


def _jsonable_records(records: list[dict]) -> list[dict]:
    return [{k: _to_jsonable(v) for k, v in rec.items()} for rec in records]


def _sample(df: pd.DataFrame, sample_rows: int) -> tuple[pd.DataFrame, bool]:
    if len(df) > sample_rows:
        return df.sample(n=sample_rows, random_state=42).sort_index(), True
    return df, False


def _build_column_info(df: pd.DataFrame) -> list[ColumnInfo]:
    cols: list[ColumnInfo] = []
    for name in df.columns:
        inferred, confidence = infer_column_type(df[name])
        sample_values = df[name].dropna().head(5).tolist()
        cols.append(
            ColumnInfo(
                name=str(name),
                inferred_type=inferred,
                confidence=round(float(confidence), 3),
                sample_values=[_to_jsonable(v) for v in sample_values],
            )
        )
    return cols


async def ingest(raw: bytes, filename: str, repo: DatasetRepository) -> UploadResponse:
    """解析并落盘，返回上传响应（含类型推断与预览）。

    raw: 文件字节流；filename: 原始文件名；repo: 存储仓库（注入）。
    """
    settings = get_settings()

    # 1. 解析
    df = read_table_file(raw, filename)
    if df.empty:
        raise ValueError("解析后无有效数据行")

    # 2. 采样（仅用于分析/预览，不落盘）
    analyzed, sampled = _sample(df, settings.sample_rows)

    # 3. 全量落盘 Parquet + SQLite 元数据
    dataset_id = repo.save_raw(df, filename)

    # 4. 类型推断 + 预览
    columns = _build_column_info(analyzed)
    preview = _jsonable_records(
        analyzed.head(PREVIEW_ROWS).replace({pd.NA: None}).to_dict(orient="records")
    )

    note = None
    if sampled:
        note = (
            f"数据量 {len(df):,} 行超过采样上限 {settings.sample_rows:,}，"
            f"已随机采样 {settings.sample_rows:,} 行用于类型推断与预览；"
            f"原始全量数据已落盘，后续分析将按需加载。"
        )

    return UploadResponse(
        dataset_id=dataset_id,
        filename=filename,
        rows=int(len(df)),
        cols=int(df.shape[1]),
        columns=columns,
        preview=preview,
        note=note,
    )
