"""Step 5 HTTP 冒烟测试：3 个分析端点返回 200 + 信封契约 + 业务字段。

运行：python -m tests.step05_http  （backend/ 下，venv 已装 fastapi/httpx/pandas/numpy/scipy）
"""
import os
import tempfile

from fastapi.testclient import TestClient

from app.main import app

SAMPLE = os.path.join(os.path.dirname(__file__), "sample.csv")


def test_main():
    with TestClient(app) as client:
        # 1) 上传样例 CSV
        with open(SAMPLE, "rb") as f:
            r = client.post("/api/v1/datasets/upload", files={"file": ("sample.csv", f, "text/csv")})
        assert r.status_code == 200, r.text
        did = r.json()["data"]["dataset_id"]
        print("upload 200, dataset_id:", did)

        # 2) 相关性（POST /analysis/correlation）
        rc = client.post(
            "/api/v1/analysis/correlation",
            json={"dataset_id": did, "type": "pearson", "columns": ["amount", "quantity"]},
        )
        assert rc.status_code == 200, rc.text
        body = rc.json()
        assert "data" in body and "explanation" in body and "meta" in body
        assert len(body["data"]["columns"]) == 2
        print("correlation 200, cols:", body["data"]["columns"])

        # 3) 假设检验 Welch t（is_member 为二分类别，amount 数值）
        rh = client.post(
            "/api/v1/analysis/hypothesis",
            json={"dataset_id": did, "test": "welch_t", "group_column": "is_member", "value_column": "amount"},
        )
        assert rh.status_code == 200, rh.text
        h = rh.json()["data"]
        assert h["test"] == "welch_t" and h["df"] is not None
        print("hypothesis(welch) 200, p=", h["p_value"], "conclusion:", h["conclusion"])

        # 4) 假设检验 卡方（category × city）
        rk = client.post(
            "/api/v1/analysis/hypothesis",
            json={"dataset_id": did, "test": "chi2", "group_column": "category", "value_column": "city"},
        )
        assert rk.status_code == 200, rk.text
        k = rk.json()["data"]
        assert k["test"] == "chi2" and k["statistic"] > 0
        print("hypothesis(chi2) 200, chi2=", k["statistic"])

        # 5) 分布检验 KS（amount）
        rd = client.post(
            "/api/v1/analysis/distribution",
            json={"dataset_id": did, "test": "ks", "column": "amount"},
        )
        assert rd.status_code == 200, rd.text
        d = rd.json()["data"]
        assert d["test"] == "ks" and isinstance(d["is_normal"], bool)
        print("distribution(ks) 200, D=", d["statistic"], "is_normal=", d["is_normal"])

    print("\nALL_STEP5_HTTP_TESTS_PASSED")


if __name__ == "__main__":
    test_main()
