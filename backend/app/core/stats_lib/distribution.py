"""分布检验（自实现）：KS 正态性检验（Lilliefors 修正）。

D = max |F_n(x) - Φ((x-x̄)/s)|
其中 F_n 为经验 CDF，Φ 为标准正态 CDF（用 scipy.stats.norm.cdf 计算）。
显著性用 Lilliefors 修正临界值：n≤50 查表（硬编码，线性插值），n>50 用 D_crit ≈ 0.886/√n (α=0.05)。
"""
import numpy as np
from scipy import stats as _stats

# Lilliefors 修正临界值（α=0.05）近似表，键为样本量 n。
# 来源：Lilliefors (1967) 常用近似临界值。n≤50 查表，n>50 用 0.886/√n。
_LILLIEFORS_TABLE = {
    4: 0.4475, 5: 0.4091, 6: 0.3689, 7: 0.3384, 8: 0.3167,
    9: 0.2998, 10: 0.2851, 11: 0.2727, 12: 0.2623, 13: 0.2531,
    14: 0.2452, 15: 0.2382, 16: 0.2319, 17: 0.2260, 18: 0.2206,
    19: 0.2156, 20: 0.2111, 21: 0.2068, 22: 0.2027, 23: 0.1989,
    24: 0.1952, 25: 0.1918, 26: 0.1885, 27: 0.1855, 28: 0.1826,
    29: 0.1798, 30: 0.1772, 31: 0.1746, 32: 0.1722, 33: 0.1699,
    34: 0.1676, 35: 0.1655, 36: 0.1634, 37: 0.1614, 38: 0.1595,
    39: 0.1576, 40: 0.1558, 41: 0.1541, 42: 0.1524, 43: 0.1508,
    44: 0.1492, 45: 0.1477, 46: 0.1462, 47: 0.1448, 48: 0.1434,
    49: 0.1420, 50: 0.1407,
}


def _lilliefors_critical(n: int) -> float:
    """返回 α=0.05 的 Lilliefors 临界值 D_crit。"""
    if n > 50:
        return 0.886 / np.sqrt(n)
    keys = sorted(_LILLIEFORS_TABLE.keys())
    if n <= keys[0]:
        return _LILLIEFORS_TABLE[keys[0]]
    if n >= keys[-1]:
        return _LILLIEFORS_TABLE[keys[-1]]
    # 线性插值
    for lo, hi in zip(keys[:-1], keys[1:]):
        if lo <= n <= hi:
            d_lo, d_hi = _LILLIEFORS_TABLE[lo], _LILLIEFORS_TABLE[hi]
            return d_lo + (d_hi - d_lo) * (n - lo) / (hi - lo)
    return _LILLIEFORS_TABLE[keys[-1]]


def _ks_p_asymptotic(d: float, n: int) -> float:
    """KS 双尾 p 值的大样本渐近近似（Kolmogorov 分布级数）：
    Q_KS(x)=2 Σ_{k=1}^∞ (-1)^{k-1} e^{-2 k² x²}, x=√n·D。
    注：这是标准 KS 近似；Lilliefors 因用样本估计参数会更严格，此处仅作参考近似。
    """
    x = np.sqrt(n) * d
    if x <= 0:
        return 1.0
    total = 0.0
    for k in range(1, 25):
        total += ((-1) ** (k - 1)) * np.exp(-2 * (k**2) * (x**2))
    p = 2 * total
    return float(min(1.0, max(0.0, p)))


def ks_normality(x: np.ndarray) -> dict:
    """返回 {'statistic': D, 'p_value': 近似p值, 'is_normal': D < D_crit(α=0.05)}（n<5 或方差为0时 'warning'）。

    D = max |F_n(x) - Φ((x-x̄)/s)|
    """
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = x.size

    if n < 5:
        return {
            "statistic": float("nan"),
            "p_value": float("nan"),
            "is_normal": False,
            "warning": f"样本量过小（n={n}<5），Lilliefors 检验结果不可靠",
        }

    xbar = float(x.mean())
    s = float(x.std(ddof=1))
    if s == 0.0:
        return {
            "statistic": 0.0,
            "p_value": float("nan"),
            "is_normal": False,
            "warning": "数据方差为 0（常数序列），无法检验正态性",
        }

    xs = np.sort(x)
    # 经验 CDF 两种定义取 max：F_n(x_i)=i/n 与 F_n(x_i)=(i-1)/n
    cdf_emp_plus = np.arange(1, n + 1) / n
    cdf_emp_minus = np.arange(0, n) / n
    # 正态参考 CDF：Φ((x-x̄)/s)
    z = (xs - xbar) / s
    phi = _stats.norm.cdf(z)
    d1 = np.abs(cdf_emp_plus - phi)
    d2 = np.abs(cdf_emp_minus - phi)
    D = float(max(d1.max(), d2.max()))

    d_crit = _lilliefors_critical(n)
    is_normal = D < d_crit
    p = _ks_p_asymptotic(D, n)
    return {"statistic": D, "p_value": p, "is_normal": is_normal, "warning": None}
