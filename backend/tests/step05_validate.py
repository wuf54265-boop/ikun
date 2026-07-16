"""Step 5 验证：自实现统计算法与 scipy 对照（浮点误差 ≤ 1e-6 / p 值 ≤ 1e-2）。

运行：python -m tests.step05_validate  （在 backend/ 目录下，venv 已装 scipy/pandas/numpy）
"""
import math
import os

import numpy as np
import pandas as pd
from scipy import stats as sps

from app.core.stats_lib import correlation as lib_corr
from app.core.stats_lib import hypothesis as lib_hyp
from app.core.stats_lib import distribution as lib_dist
from app.services import stats as svc
from app.schemas.stats import (
    CorrelationRequest,
    DistributionRequest,
    HypothesisRequest,
)

PASS = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name} {detail}")
    if not cond:
        raise AssertionError(f"{name} FAILED {detail}")
    PASS.append(name)


def test_pearson():
    # 完全正相关 [1,2,3] vs [2,4,6]
    X = np.array([[1.0, 2.0], [2.0, 4.0], [3.0, 6.0]])
    res = lib_corr.pearson_with_p(X)
    r = res["r"][0, 1]
    p = res["p_values"][0, 1]
    check("pearson 完全正相关 r≈1", abs(r - 1.0) < 1e-9, f"r={r}")
    check("pearson 完全正相关 p=0", p == 0.0, f"p={p}")

    # 与 scipy.stats.pearsonr 对照（非完全相关）
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y = np.array([2.0, 1.0, 4.0, 3.0, 5.0])
    X2 = np.column_stack([x, y])
    res2 = lib_corr.pearson_with_p(X2)
    sr, sp = sps.pearsonr(x, y)
    check("pearson vs scipy r", abs(res2["r"][0, 1] - sr) < 1e-9, f"mine={res2['r'][0,1]} scipy={sr}")
    check("pearson vs scipy p", abs(res2["p_values"][0, 1] - sp) < 1e-6, f"mine={res2['p_values'][0,1]} scipy={sp}")

    # 独立随机数据 r 接近 0
    rng = np.random.default_rng(7)
    a = rng.normal(0, 1, 500)
    b = rng.normal(0, 1, 500)
    Xr = np.column_stack([a, b])
    rr = lib_corr.pearson_with_p(Xr)["r"][0, 1]
    check("pearson 独立随机 |r|<0.2", abs(rr) < 0.2, f"r={rr}")

    # 常数列 → NaN，不崩溃
    Xc = np.column_stack([np.array([1.0, 2.0, 3.0]), np.array([5.0, 5.0, 5.0])])
    rc = lib_corr.pearson_with_p(Xc)
    check("pearson 常数列 r=NaN", math.isnan(rc["r"][0, 1]), f"r={rc['r'][0,1]}")


def test_welch_t():
    x = np.array([10.0, 11.0, 12.0, 13.0, 14.0])
    y = np.array([20.0, 21.0, 22.0, 23.0, 24.0])
    res = lib_hyp.welch_t(x, y)
    st, sp = sps.ttest_ind(x, y, equal_var=False)
    check("welch t 统计量 vs scipy", abs(res["statistic"] - st) < 1e-9, f"mine={res['statistic']} scipy={st}")
    check("welch t p vs scipy", abs(res["p_value"] - sp) < 1e-6, f"mine={res['p_value']} scipy={sp}")
    check("welch t p<0.05", res["p_value"] < 0.05, f"p={res['p_value']}")
    # Cohen's d 手动核对
    n1, n2 = len(x), len(y)
    m1, m2 = x.mean(), y.mean()
    v1, v2 = x.var(ddof=1), y.var(ddof=1)
    cd = abs(m1 - m2) / math.sqrt((v1 + v2) / 2)
    check("welch cohens_d", abs(res["cohens_d"] - cd) < 1e-9, f"mine={res['cohens_d']} ref={cd}")

    # 退化：两组方差均为 0 且均值相等 → t=0,p=1
    g1 = np.array([3.0, 3.0, 3.0])
    g2 = np.array([3.0, 3.0, 3.0])
    r2 = lib_hyp.welch_t(g1, g2)
    check("welch 退化(等均值) t=0", r2["statistic"] == 0.0, f"t={r2['statistic']}")
    check("welch 退化(等均值) p=1", r2["p_value"] == 1.0, f"p={r2['p_value']}")

    # 退化：两组方差均为 0 且均值不同 → 抛 ValueError
    g3 = np.array([3.0, 3.0])
    g4 = np.array([5.0, 5.0])
    try:
        lib_hyp.welch_t(g3, g4)
        check("welch 退化(异均值) 抛错", False, "未抛错")
    except ValueError:
        check("welch 退化(异均值) 抛错", True)


def test_chi2():
    O = np.array([[10, 20], [20, 10]])
    res = lib_hyp.chi2_independence(O)
    chi2, p, dof, exp = sps.chi2_contingency(O, correction=False)
    check("chi2 统计量 vs scipy", abs(res["statistic"] - chi2) < 1e-6, f"mine={res['statistic']} scipy={chi2}")
    check("chi2 df vs scipy", res["df"] == dof, f"mine={res['df']} scipy={dof}")
    n = O.sum()
    cv = math.sqrt(chi2 / (n * min(O.shape[0] - 1, O.shape[1] - 1)))
    check("chi2 cramers_v", abs(res["cramers_v"] - cv) < 1e-6, f"mine={res['cramers_v']} ref={cv}")
    check("chi2 p<0.05 (关联)", res["p_value"] < 0.05, f"p={res['p_value']}")

    # 期望频数过低 warning
    small = np.array([[1, 9], [0, 10]])
    rs = lib_hyp.chi2_independence(small)
    check("chi2 期望频数过低 warning", rs["warning"] is not None and "Fisher" in rs["warning"], f"warn={rs['warning']}")

    # 全零行/列剔除（移除后仍为 ≥2×2）
    with_zero = np.array([[5, 5, 0], [5, 5, 0], [1, 2, 0]])  # 第3列全零
    rz = lib_hyp.chi2_independence(with_zero)
    check("chi2 剔除全零列 warning", rz["warning"] is not None and "全零" in rz["warning"], f"warn={rz['warning']}")


def test_ks_normality():
    rng = np.random.default_rng(42)
    # 正态分布 → is_normal True
    x = rng.normal(0, 1, 300)
    res = lib_dist.ks_normality(x)
    ks = sps.kstest(x, sps.norm(x.mean(), x.std(ddof=1)).cdf)
    check("ks D vs scipy 统计一致", abs(res["statistic"] - ks.statistic) < 1e-6, f"mine={res['statistic']} scipy={ks.statistic}")
    check("ks 正态样本 is_normal=True", res["is_normal"] == True, f"D={res['statistic']}")

    # 均匀分布 → is_normal False
    u = rng.uniform(0, 1, 300)
    resu = lib_dist.ks_normality(u)
    ksu = sps.kstest(u, sps.norm(u.mean(), u.std(ddof=1)).cdf)
    check("ks D vs scipy 统计一致(uniform)", abs(resu["statistic"] - ksu.statistic) < 1e-6, f"mine={resu['statistic']} scipy={ksu.statistic}")
    check("ks 均匀样本 is_normal=False", resu["is_normal"] == False, f"D={resu['statistic']}")

    # n<5 warning
    tiny = np.array([1.0, 2.0, 3.0])
    rt = lib_dist.ks_normality(tiny)
    check("ks n<5 warning", rt["warning"] is not None and "样本量过小" in rt["warning"], f"warn={rt['warning']}")


def test_service_integration():
    df = pd.DataFrame(
        {
            # group A 低、group B 高（Welch 应显著）
            "amount": [10.0, 11.0, 12.0, 13.0, 30.0, 31.0, 32.0, 33.0],
            "quantity": [1.0, 2.0, 1.0, 2.0, 3.0, 4.0, 3.0, 4.0],
            "group": ["A", "A", "A", "A", "B", "B", "B", "B"],
            # 与 group 关联的类别列（A 多 x、B 多 y）→ 卡方应显著
            "cat": ["x", "x", "x", "y", "y", "y", "y", "x"],
        }
    )
    corr = svc.correlation(df, CorrelationRequest(dataset_id="t", type="pearson", columns=["amount", "quantity"]))
    check("svc correlation 形状", len(corr.columns) == 2 and len(corr.matrix) == 2, f"cols={corr.columns}")

    hyp = svc.hypothesis(
        df, HypothesisRequest(dataset_id="t", test="welch_t", group_column="group", value_column="amount")
    )
    check("svc welch p<0.05", hyp.p_value < 0.05, f"p={hyp.p_value}")

    chi = svc.hypothesis(df, HypothesisRequest(dataset_id="t", test="chi2", group_column="group", value_column="cat"))
    check("svc chi2 出结果", chi.statistic > 0, f"chi2={chi.statistic}")

    dist = svc.distribution(df, DistributionRequest(dataset_id="t", test="ks", column="amount"))
    check("svc distribution 字段完整", dist.test == "ks" and isinstance(dist.is_normal, bool), f"is_normal={dist.is_normal}")


def main():
    print("=== Step 5 自实现统计验证 ===")
    test_pearson()
    test_welch_t()
    test_chi2()
    test_ks_normality()
    test_service_integration()
    print(f"\nALL_STEP5_TESTS_PASSED ({len(PASS)} checks)")


if __name__ == "__main__":
    main()
