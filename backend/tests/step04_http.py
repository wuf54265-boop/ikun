"""Step 4 HTTP 端点验证（等价于 curl 验证）。

运行：python -m tests.step04_http
验证：POST /clean 与 POST /anomalies 返回 200 + 信封 {data,explanation,meta}
"""
import io
import os
import tempfile

from fastapi.testclient import TestClient

from app.main import app
from app.store import db


def test_main():
    with TestClient(app) as client:
        # 1) 上传一个含缺失 + 异常的数据
        csv_text = "amount,qty\n10,1\n20,2\n,3\n40,4\n1000,5\n"
        r = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("step4.csv", csv_text.encode(), "text/csv")},
        )
        assert r.status_code == 200, r.text
        did = r.json()["data"]["dataset_id"]
        print("upload 200, dataset_id:", did)

        # 2) POST /clean（中位数填充 amount）
        rc = client.post(
            f"/api/v1/datasets/{did}/clean",
            json={"strategies": [{"column": "amount", "strategy": "median"}]},
        )
        assert rc.status_code == 200, rc.text
        body = rc.json()
        assert "data" in body and "explanation" in body and "meta" in body
        cd = body["data"]
        assert cd["after_rows"] == 5 and "amount" in cd["changed_columns"]
        print("clean 200, after_rows:", cd["after_rows"], "changed:", cd["changed_columns"])

        # 3) POST /anomalies (iqr)
        ra = client.post(
            f"/api/v1/datasets/{did}/anomalies",
            json={"method": "iqr", "columns": ["amount"], "threshold": 1.5},
        )
        assert ra.status_code == 200, ra.text
        ad = ra.json()["data"]
        assert ad["anomaly_count"] >= 1
        print("anomalies(iqr) 200, count:", ad["anomaly_count"])

        # 4) POST /anomalies (isolation_forest)
        rf = client.post(
            f"/api/v1/datasets/{did}/anomalies",
            json={"method": "isolation_forest", "columns": [], "threshold": 0.1},
        )
        assert rf.status_code == 200, rf.text
        af = rf.json()["data"]
        assert af["method"] == "isolation_forest"
        print("anomalies(isolation_forest) 200, count:", af["anomaly_count"])

        # 5) 404
        r404 = client.post(
            "/api/v1/datasets/nope/clean", json={"strategies": []}
        )
        assert r404.status_code == 404
        print("404 路径 OK")

        print("\nALL_STEP4_HTTP_TESTS_PASSED")


if __name__ == "__main__":
    test_main()
