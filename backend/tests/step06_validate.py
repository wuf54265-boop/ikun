"""Step 6 验证：OLS / K-Means 自实现 vs statsmodels / sklearn 对照。

运行：python -m tests.step06_validate  （在 backend/ 目录下，venv 已装 statsmodels/sklearn/pandas/numpy/scipy）
"""
import numpy as np

from app.core.stats_lib import kmeans as lib_km
from app.core.stats_lib import ols as lib_ols
from app.services import modeling as svc

PASS = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name} {detail}")
    if not cond:
        raise AssertionError(f"{name} FAILED {detail}")
    PASS.append(name)


def test_ols():
    import statsmodels.api as sm

    rng = np.random.default_rng(0)
    n = 300
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(0, 1, n)
    X = np.column_stack([x1, x2])
    y = 2.0 * x1 + 3.0 * x2 + 1.0 + rng.normal(0, 0.01, n)

    res = lib_ols.ols(X, y)
    Xs = sm.add_constant(X)
    m = sm.OLS(y, Xs).fit()

    # 系数顺序：我们的 [const, x1, x2]；statsmodels 同序（位置索引 0,1,2）
    mine = [res["coefficients"][0]["coef"], res["coefficients"][1]["coef"], res["coefficients"][2]["coef"]]
    ref = [float(m.params[0]), float(m.params[1]), float(m.params[2])]
    max_beta_err = max(abs(a - b) for a, b in zip(mine, ref))
    check("ols 系数 vs statsmodels 误差<1e-6", max_beta_err < 1e-6, f"err={max_beta_err:.2e}")

    check("ols R² vs statsmodels 误差<1e-6", abs(res["r_squared"] - float(m.rsquared)) < 1e-6,
          f"mine={res['r_squared']:.8f} sm={float(m.rsquared):.8f}")
    check("ols 调整R² vs statsmodels 误差<1e-6", abs(res["adj_r_squared"] - float(m.rsquared_adj)) < 1e-6,
          f"mine={res['adj_r_squared']:.8f} sm={float(m.rsquared_adj):.8f}")

    # 标准误 / t / p 也应与 statsmodels 一致
    se_mine = [res["coefficients"][0]["std_err"], res["coefficients"][1]["std_err"], res["coefficients"][2]["std_err"]]
    se_ref = [float(m.bse[0]), float(m.bse[1]), float(m.bse[2])]
    max_se_err = max(abs((a or 0) - b) for a, b in zip(se_mine, se_ref))
    check("ols 标准误 vs statsmodels 误差<1e-4", max_se_err < 1e-4, f"err={max_se_err:.2e}")

    p_ref = [float(m.pvalues[0]), float(m.pvalues[1]), float(m.pvalues[2])]
    p_mine = [res["coefficients"][i]["p_value"] for i in range(3)]
    max_p_err = max(abs((a or 0) - b) for a, b in zip(p_mine, p_ref))
    check("ols p 值 vs statsmodels 误差<1e-4", max_p_err < 1e-4, f"err={max_p_err:.2e}")

    # 残差 / 拟合长度正确
    check("ols 残差长度=n", len(res["residuals"]) == n)
    check("ols 拟合长度=n", len(res["fitted"]) == n)


def test_ols_multicollinearity():
    rng = np.random.default_rng(1)
    n = 100
    x1 = rng.normal(0, 1, n)
    # x2 ≈ 2*x1（极小扰动）→ 近共线，条件数极大
    x2 = 2.0 * x1 + 1e-12 * rng.normal(0, 1, n)
    X = np.column_stack([x1, x2])
    y = x1 + rng.normal(0, 0.01, n)
    res = lib_ols.ols(X, y)
    check("ols 共线性 warning 命中", res["warning"] is not None and ("共线" in res["warning"] or "奇异" in res["warning"]),
          f"warn={res['warning']}")
    # 仍返回有限系数（不崩）
    check("ols 共线性仍返回有限系数", all(np.isfinite([c["coef"] for c in res["coefficients"]])))


def test_kmeans():
    from sklearn.cluster import KMeans
    from sklearn.datasets import load_iris
    from sklearn.metrics import adjusted_rand_score

    iris = load_iris()
    X = iris.data[:, :2]  # 前两维（sepal 长/宽，versicolor 与 virginica 在此有重叠）
    y_true = iris.target

    res = lib_km.kmeans(X, k=3, seed=42)
    check("kmeans 标签无空簇(3类)", len(np.unique(res["labels"])) == 3, f"unique={np.unique(res['labels'])}")
    check("kmeans 质心形状 (3,2)", res["centroids"].shape == (3, 2))
    check("kmeans 无 NaN 质心", not np.any(np.isnan(res["centroids"])))

    ari_mine = adjusted_rand_score(y_true, res["labels"])
    # 参照：sklearn KMeans 在同一数据上的 ARI（前两维重叠导致二者都 ≈0.6，非实现问题）
    sk = KMeans(n_clusters=3, n_init=10, random_state=42).fit(X)
    ari_sk = adjusted_rand_score(y_true, sk.labels_)
    check("kmeans 捕捉到真实结构 ARI≥0.5", ari_mine >= 0.5, f"ARI={ari_mine:.3f}")
    check("kmeans 与 sklearn ARI 相当(差距<0.1)", ari_mine >= ari_sk - 0.1,
          f"mine={ari_mine:.3f} sklearn={ari_sk:.3f}")

    # 全 4 维 Iris（特征可分）→ 我们自实现 K-Means 也能达到 ARI≥0.7
    X4 = iris.data
    res4 = lib_km.kmeans(X4, k=3, seed=42)
    ari4 = adjusted_rand_score(y_true, res4["labels"])
    check("kmeans 全4维 Iris ARI≥0.7", ari4 >= 0.7, f"ARI={ari4:.3f}")


def test_silhouette():
    # 单簇（全等点）→ 轮廓系数 = 0
    X0 = np.zeros((50, 2))
    r0 = lib_km.kmeans(X0, k=2, seed=1)
    sil0 = lib_km.silhouette_score(X0, r0["labels"])
    check("silhouette 单簇(全等)≈0", sil0 == 0.0, f"sil={sil0}")

    # 明显分离 → 轮廓系数 > 0.5
    rng = np.random.default_rng(0)
    blobs = np.vstack([
        rng.normal([0, 0], 0.1, size=(60, 2)),
        rng.normal([10, 10], 0.1, size=(60, 2)),
        rng.normal([10, 0], 0.1, size=(60, 2)),
    ])
    rk = lib_km.kmeans(blobs, k=3, seed=42)
    sil = lib_km.silhouette_score(blobs, rk["labels"])
    check("silhouette 明显分离>0.5", sil > 0.5, f"sil={sil:.3f}")


def test_empty_cluster():
    # 说明：k-means++ 把质心初始化在数据点（每个质心初始至少带 1 个点），最近质心
    # 分配保证每个质心始终保留其初始化点，因此正常数据下空簇几乎不会发生——空簇
    # 重初始化是防御性逻辑。本测试验证：极端 k 下算法始终稳健（标签合法、无 NaN、
    # 正常收敛），即该防御逻辑不会把结果搞坏。
    rng = np.random.default_rng(3)
    X = np.vstack([
        rng.normal([0, 0], 0.1, size=(60, 2)),
        rng.normal([10, 10], 0.1, size=(60, 2)),
        rng.normal([10, 0], 0.1, size=(60, 2)),
    ])
    for k in range(2, 25):
        for seed in range(10):
            r = lib_km.kmeans(X, k=k, seed=seed)
            assert set(np.union1d(np.unique(r["labels"]), [])).issubset(set(range(k))), f"非法标签 k={k}"
            assert r["labels"].shape[0] == X.shape[0]
            assert not np.any(np.isnan(r["centroids"])), f"NaN 质心 k={k}"
            assert 1 <= r["iterations"] <= 300
    check("kmeans 极端 k 下稳健（无 NaN / 合法标签 / 收敛）", True)


def test_service_integration():
    import pandas as pd

    rng = np.random.default_rng(5)
    n = 120
    df = pd.DataFrame(
        {
            "x1": rng.normal(0, 1, n),
            "x2": rng.normal(0, 1, n),
            "x3": rng.normal(0, 1, n),
        }
    )
    df["y"] = 2.0 * df["x1"] + 3.0 * df["x2"] + 1.0 + rng.normal(0, 0.05, n)

    reg = svc.regression(
        df,
        __import__("app.schemas.modeling", fromlist=["RegressionRequest"]).RegressionRequest(
            dataset_id="t", target="y", features=["x1", "x2", "x3"], standardize=False
        ),
    )
    check("svc regression 系数含 const", reg.coefficients[0].name == "const", f"first={reg.coefficients[0].name}")
    check("svc regression R²>0.9", reg.r_squared > 0.9, f"R²={reg.r_squared:.4f}")
    check("svc regression 残差图非空", len(reg.residual_plot.residuals) == n)
    check("svc regression qq_data 非空", len(reg.residual_plot.qq_data) > 0)

    clu = svc.clustering(
        df,
        __import__("app.schemas.modeling", fromlist=["ClusteringRequest"]).ClusteringRequest(
            dataset_id="t", features=["x1", "x2", "x3"], auto_k=True
        ),
    )
    check("svc clustering auto_k 返回 k_curve", len(clu.k_curve) > 0, f"k={clu.k}")
    check("svc clustering 散点非空", len(clu.scatter) > 0, f"scatter={len(clu.scatter)}")
    check("svc clustering 质心维度=3", len(clu.centroids[0]) == 3, f"dim={len(clu.centroids[0])}")


def main():
    print("=== Step 6 建模（OLS / K-Means）自实现验证 ===")
    test_ols()
    test_ols_multicollinearity()
    test_kmeans()
    test_silhouette()
    test_empty_cluster()
    test_service_integration()
    print(f"\nALL_STEP6_TESTS_PASSED ({len(PASS)} checks)")


if __name__ == "__main__":
    main()
