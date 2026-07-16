"""Step 6 HTTP 冒烟测试：建模两个端点返回 200 + 信封契约 + 业务字段。

运行：python -m tests.step06_http  （backend/ 下，venv 已装 fastapi/httpx/pandas/numpy/scipy）
"""
import csv
import os
import tempfile

from fastapi.testclient import TestClient

from app.main import app

SAMPLE = os.path.join(os.path.dirname(__file__), "step06_sample.csv")


def _make_sample():
    import numpy as np

    rng = np.random.default_rng(11)
    n = 150
    # 回归目标 y = 2x1 + 3x2 + 1 + 噪声
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(0, 1, n)
    x3 = rng.normal(0, 1, n)
    y = 2.0 * x1 + 3.0 * x2 + 1.0 + rng.normal(0, 0.05, n)
    # 再加 3 个明显分离簇（用于聚类 auto_k 选 K≈3），与回归特征无关
    cx = np.array([5.0, -5.0, 0.0])
    cy = np.array([5.0, -5.0, 0.0])
    labels = rng.integers(0, 3, n)
    cx_col = cx[labels] + rng.normal(0, 0.2, n)
    cy_col = cy[labels] + rng.normal(0, 0.2, n)
    with open(SAMPLE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["x1", "x2", "x3", "y", "cx", "cy"])
        for i in range(n):
            w.writerow([f"{x1[i]:.4f}", f"{x2[i]:.4f}", f"{x3[i]:.4f}", f"{y[i]:.4f}", f"{cx_col[i]:.4f}", f"{cy_col[i]:.4f}"])


def test_main():
    _make_sample()
    with TestClient(app) as client:
        # 1) 上传样例 CSV
        with open(SAMPLE, "rb") as f:
            r = client.post("/api/v1/datasets/upload", files={"file": ("step06_sample.csv", f, "text/csv")})
        assert r.status_code == 200, r.text
        did = r.json()["data"]["dataset_id"]
        print("upload 200, dataset_id:", did)

        # 2) OLS 回归
        rr = client.post(
            "/api/v1/modeling/regression",
            json={"dataset_id": did, "target": "y", "features": ["x1", "x2", "x3"], "standardize": False},
        )
        assert rr.status_code == 200, rr.text
        body = rr.json()
        assert "data" in body and "explanation" in body and "meta" in body
        d = body["data"]
        assert d["coefficients"][0]["name"] == "const"
        assert d["r_squared"] > 0.9
        assert len(d["residual_plot"]["residuals"]) > 0
        print("regression 200, R²=", d["r_squared"], "adj_R²=", d["adj_r_squared"])

        # 3) K-Means 聚类（auto_k）
        rc = client.post(
            "/api/v1/modeling/clustering",
            json={"dataset_id": did, "features": ["cx", "cy"], "auto_k": True},
        )
        assert rc.status_code == 200, rc.text
        c = rc.json()["data"]
        assert len(c["centroids"]) >= 2
        assert len(c["k_curve"]) > 0
        assert len(c["scatter"]) > 0
        print("clustering 200, k=", c["k"], "silhouette=", c["silhouette"], "inertia=", c["inertia"])

    print("\nALL_STEP6_HTTP_TESTS_PASSED")


if __name__ == "__main__":
    test_main()
