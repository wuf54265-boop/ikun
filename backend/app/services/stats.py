"""统计分析服务：相关性 / 假设检验 / 分布检验。"""
import numpy as np
import pandas as pd

from app.core.stats_lib import correlation as lib_corr
from app.core.stats_lib import hypothesis as lib_hyp
from app.core.stats_lib import distribution as lib_dist
from app.schemas.stats import (
    CorrelationData,
    CorrelationRequest,
    DistributionData,
    DistributionRequest,
    HypothesisData,
    HypothesisRequest,
)


def _round4(v):
    """四舍五入到 4 位；NaN → None（供 JSON 安全传输）。"""
    if v is None:
        return None
    f = float(v)
    if np.isnan(f) or np.isinf(f):
        return None
    return round(f, 4)


def correlation(df: pd.DataFrame, body: CorrelationRequest) -> CorrelationData:
    """Pearson 相关 + 显著性。body.columns 非空且≥2 时只对指定列算，否则对所有数值列算。"""
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not body.columns:
        cols = numeric_cols
    else:
        cols = [c for c in body.columns if c in df.columns]
    # 仅保留数值列
    cols = [c for c in cols if c in numeric_cols]
    if len(cols) < 2:
        raise ValueError("相关性分析至少需要 2 个有效数值列（当前不足）")

    if body.type != "pearson":
        raise ValueError(f"暂仅支持 pearson 相关，收到 type={body.type!r}")

    X = df[cols].to_numpy(dtype=float)  # 保留 NaN，pearson 内部逐对剔除
    res = lib_corr.pearson_with_p(X)
    r = res["r"]
    p = res["p_values"]
    k = len(cols)
    matrix = [[_round4(r[i, j]) for j in range(k)] for i in range(k)]
    pvals = [[_round4(p[i, j]) for j in range(k)] for i in range(k)]
    return CorrelationData(columns=cols, matrix=matrix, p_values=pvals)


def hypothesis(df: pd.DataFrame, body: HypothesisRequest) -> HypothesisData:
    """假设检验：welch_t（两组均值）或 chi2（独立性）。"""
    if body.test == "welch_t":
        if not body.group_column or not body.value_column:
            raise ValueError("welch_t 需提供 group_column（二分类别列）与 value_column（数值列）")
        if body.group_column not in df.columns:
            raise ValueError(f"分组列不存在：{body.group_column}")
        if body.value_column not in df.columns or not pd.api.types.is_numeric_dtype(df[body.value_column]):
            raise ValueError(f"数值列不存在或非数值：{body.value_column}")
        groups = df[body.group_column].dropna()
        uniq = groups.unique()
        if len(uniq) != 2:
            raise ValueError(
                f"Welch t 要求二分类别列，{body.group_column} 有 {len(uniq)} 个不同取值"
            )
        g1 = df.loc[df[body.group_column] == uniq[0], body.value_column].to_numpy(dtype=float)
        g2 = df.loc[df[body.group_column] == uniq[1], body.value_column].to_numpy(dtype=float)
        res = lib_hyp.welch_t(g1, g2)
        return HypothesisData(
            test="welch_t",
            statistic=_round4(res["statistic"]),
            df=_round4(res["df"]),
            p_value=_round4(res["p_value"]),
            effect_size=_round4(res["cohens_d"]),
            conclusion=_conclusion(res["p_value"]),
            warning=res.get("warning"),
        )

    if body.test == "chi2":
        if body.cont_table:
            cont = np.asarray(body.cont_table, dtype=float)
        else:
            if not body.group_column or not body.value_column:
                raise ValueError("chi2 需提供 group_column + value_column，或直接给 cont_table")
            if body.group_column not in df.columns or body.value_column not in df.columns:
                raise ValueError("chi2 的行/列变量列不存在")
            cont = pd.crosstab(df[body.group_column], df[body.value_column]).to_numpy(dtype=float)
        res = lib_hyp.chi2_independence(cont)
        return HypothesisData(
            test="chi2",
            statistic=_round4(res["statistic"]),
            df=_round4(res["df"]),
            p_value=_round4(res["p_value"]),
            effect_size=_round4(res["cramers_v"]),
            conclusion=_conclusion(res["p_value"]),
            warning=res.get("warning"),
        )

    raise ValueError(f"不支持的检验类型：{body.test!r}（仅支持 welch_t / chi2）")


def distribution(df: pd.DataFrame, body: DistributionRequest) -> DistributionData:
    """KS 正态性检验（Lilliefors 修正）。"""
    if body.column not in df.columns:
        raise ValueError(f"列不存在：{body.column}")
    if not pd.api.types.is_numeric_dtype(df[body.column]):
        raise ValueError(f"KS 正态性检验要求数值列：{body.column}")
    if body.test != "ks":
        raise ValueError(f"暂仅支持 ks 正态性检验，收到 test={body.test!r}")
    x = df[body.column].to_numpy(dtype=float)
    res = lib_dist.ks_normality(x)
    return DistributionData(
        test="ks",
        statistic=_round4(res["statistic"]),
        p_value=_round4(res["p_value"]),
        is_normal=bool(res["is_normal"]),
    )


def _conclusion(p_value: float) -> str:
    if p_value is None or (isinstance(p_value, float) and np.isnan(p_value)):
        return "p 值无定义，无法得出结论"
    if p_value < 0.05:
        return "拒绝原假设，存在显著差异/关联（p<0.05）"
    return "无法拒绝原假设（p≥0.05）"
