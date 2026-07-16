"""假设检验（自实现）：Welch t / 卡方独立性。

- Welch t: t=(x̄1-x̄2)/√(s1²/n1+s2²/n2)，df 用 Welch-Satterthwaite，p 用 t 分布双尾。
- 卡方: χ²=Σ(O-E)²/E，E=行和×列和/N，df=(r-1)(c-1)，效应量 Cramér's V。
"""
import numpy as np
from scipy import stats as _stats


def welch_t(x: np.ndarray, y: np.ndarray) -> dict:
    """返回 {'statistic','df','p_value','cohens_d'}（退化时附带 'warning'）。

    t = (x̄₁-x̄₂) / √(s₁²/n₁ + s₂²/n₂)
    df = (s₁²/n₁ + s₂²/n₂)² / [ (s₁²/n₁)²/(n₁-1) + (s₂²/n₂)²/(n₂-1) ]  (Welch–Satterthwaite)
    效应量: Cohen's d = |x̄₁-x̄₂| / √((s₁²+s₂²)/2)
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x = x[~np.isnan(x)]
    y = y[~np.isnan(y)]
    n1, n2 = x.size, y.size
    if n1 == 0 or n2 == 0:
        raise ValueError("Welch t 检验要求两组均非空（存在全为 NaN 的组）")
    m1, m2 = float(x.mean()), float(y.mean())
    v1 = float(x.var(ddof=1))
    v2 = float(y.var(ddof=1))

    # 退化：两组方差均为 0
    if v1 == 0.0 and v2 == 0.0:
        if m1 == m2:
            # 两组都是常数且相等 → 无差异
            return {
                "statistic": 0.0,
                "df": float(n1 + n2 - 2),
                "p_value": 1.0,
                "cohens_d": 0.0,
                "warning": "两组方差均为 0（常数序列）且均值相等，无统计差异",
            }
        # 两组都是常数但均值不同 → t 统计量 0/0 无定义
        raise ValueError(
            "Welch t 检验退化：两组方差均为 0 且均值不同，t 统计量无定义（0/0）"
        )

    # t = (x̄₁-x̄₂) / √(s₁²/n₁ + s₂²/n₂)
    se = np.sqrt(v1 / n1 + v2 / n2)
    t = (m1 - m2) / se
    # df = (s₁²/n₁ + s₂²/n₂)² / [ (s₁²/n₁)²/(n₁-1) + (s₂²/n₂)²/(n₂-1) ]
    df = (v1 / n1 + v2 / n2) ** 2 / (
        (v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1)
    )
    # 双尾 p 值
    p = float(2 * (1 - _stats.t.cdf(abs(t), df=df)))
    # Cohen's d = |x̄₁-x̄₂| / √((s₁²+s₂²)/2)
    cohens_d = float(abs(m1 - m2) / np.sqrt((v1 + v2) / 2))
    return {"statistic": float(t), "df": float(df), "p_value": p, "cohens_d": cohens_d}


def chi2_independence(cont_table: np.ndarray) -> dict:
    """输入 cont_table: 列联表 (r×c)，返回 {'statistic','df','p_value','cramers_v'}（退化时 'warning'）。

    列联表 O(r×c), Eᵢⱼ = (行和ᵢ × 列和ⱼ) / N
    χ² = Σ (O-E)²/E
    df = (r-1)(c-1)
    效应量: Cramér's V = √(χ² / (N · min(r-1, c-1)))
    """
    O = np.asarray(cont_table, dtype=float)
    if O.ndim != 2:
        raise ValueError("列联表必须是二维数组 (r×c)")

    # 剔除全零行/列（记录是否发生，便于在 warning 中标注）
    orig_r, orig_c = O.shape
    O = O[~np.all(O == 0, axis=1)]  # 删全零行
    O = O[:, ~np.all(O == 0, axis=0)]  # 删全零列
    r, c = O.shape
    if r < 2 or c < 2:
        raise ValueError("列联表去除全零行列后至少需要 2×2，才能做独立性检验")

    N = float(O.sum())
    row_sum = O.sum(axis=1, keepdims=True)
    col_sum = O.sum(axis=0, keepdims=True)
    # Eᵢⱼ = (行和ᵢ × 列和ⱼ) / N
    E = row_sum @ col_sum / N
    # χ² = Σ (O-E)²/E
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2 = float(np.sum(np.where(E > 0, (O - E) ** 2 / E, 0.0)))
    # df = (r-1)(c-1)
    df = (r - 1) * (c - 1)
    # p 值（卡方分布右尾）
    p = float(_stats.chi2.sf(chi2, df=df))
    # Cramér's V = √(χ² / (N · min(r-1, c-1)))
    cramers_v = float(np.sqrt(chi2 / (N * min(r - 1, c - 1))))

    # 期望频数过低检查
    warning = None
    notes = []
    if np.any(E < 1):
        notes.append("存在期望频数 < 1 的单元格")
    if np.mean(E < 5) > 0.2:
        notes.append(">20% 单元格期望频数 < 5")
    if notes:
        warning = "；".join(notes) + "，建议改用 Fisher 精确检验"
    if r != orig_r or c != orig_c:
        dropped = (orig_r - r) + (orig_c - c)
        w = f"已自动剔除 {dropped} 个全零行/列"
        warning = f"{w}；{warning}" if warning else w

    return {
        "statistic": chi2,
        "df": float(df),
        "p_value": p,
        "cramers_v": cramers_v,
        "warning": warning,
    }
