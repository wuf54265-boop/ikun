"""列类型推断工具：数值 / 类别 / 日期 / 文本 / 布尔，并给出置信度。

推断优先级（见产品规划「自动数据理解」）：
1. 先用 pandas 原生 dtype 判断（最可靠，置信度最高）。
2. 对象类型再按字符串内容 + 正则辅助：
   - 布尔：取值落在布尔词表且唯一值 <= 2
   - 日期/时间：满足日期正则的比例 > 0.8
   - 数值：能转 float 的比例 > 0.9
   - 类别：唯一值数相对行数较低（高基数退化为 text）
这是「类型推断逻辑」的单一可信源，ingestion 与 profiling 都复用它，保证两端一致。
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

BOOL_VALUES = {
    "true", "false", "yes", "no", "是", "否", "0", "1",
    "y", "n", "t", "f", "真", "假",
}
DATE_RE = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}")
DATETIME_RE = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}")


def infer_column_type(series: pd.Series) -> tuple[str, float]:
    """返回 (inferred_type, confidence)。

    inferred_type ∈ {numeric, boolean, datetime, categorical, text}
    confidence 为 0~1 的启发式置信度，仅用于展示，不影响分析。
    """
    s = series.dropna()
    n = len(s)
    if n == 0:
        return "text", 0.0

    dt = series.dtype
    if pd.api.types.is_bool_dtype(dt):
        return "boolean", 1.0
    if pd.api.types.is_datetime64_any_dtype(dt):
        return "datetime", 1.0
    if pd.api.types.is_numeric_dtype(dt):
        # 低基数的 0/1 整数更可能是布尔
        uniq = set(pd.unique(s.dropna()))
        if uniq <= {0, 1} and series.nunique(dropna=True) <= 2:
            return "boolean", 0.9
        return "numeric", 1.0

    # 对象 / 字符串类型：按内容推断
    strs = s.astype(str)
    lowered = strs.str.lower().str.strip()

    # 布尔
    if lowered.isin(BOOL_VALUES).all() and lowered.nunique() <= 2:
        return "boolean", 0.95

    # 日期 / 时间
    if lowered.str.match(DATETIME_RE).mean() > 0.8:
        return "datetime", 0.9
    if lowered.str.match(DATE_RE).mean() > 0.8:
        return "datetime", 0.85

    # 数值：能转 float 的比例高
    numeric_ratio = pd.to_numeric(strs, errors="coerce").notna().mean()
    if numeric_ratio > 0.9:
        return "numeric", float(round(numeric_ratio, 3))

    # 类别：基数相对行数低
    nunique = int(s.nunique())
    if nunique <= max(2, int(0.5 * n)) and nunique <= 50:
        return "categorical", 0.8
    if nunique <= 0.9 * n:
        return "categorical", 0.6

    return "text", 0.7


def is_numeric_type(inferred_type: str) -> bool:
    return inferred_type == "numeric"
