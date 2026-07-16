"""Step 3 HTTP 冒烟：用 FastAPI TestClient 验证 upload/profile/quality 端点与信封。

运行前需安装依赖：pip install fastapi uvicorn pandas numpy pyarrow pydantic-settings python-multipart httpx
"""
from __future__ import annotations

import os
import tempfile

# 在导入 app 前把存储指到临时目录，避免污染项目 ./data
_TMP = tempfile.mkdtemp(prefix="ada_http_")
os.environ["DATA_DIR"] = _TMP
os.environ["DB_PATH"] = os.path.join(_TMP, "meta.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

SAMPLE = os.path.join(os.path.dirname(__file__), "sample.csv")


def test_main():
    # 用 with 进入上下文，触发 lifespan（建表 init_db）
    with TestClient(app) as client:
        # 1) upload
        with open(SAMPLE, "rb") as f:
            r = client.post(
                "/api/v1/datasets/upload",
                files={"file": ("sample.csv", f, "text/csv")},
            )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "data" in body and "explanation" in body and "meta" in body
        did = body["data"]["dataset_id"]
        print("upload 200, dataset_id:", did, "rows:", body["data"]["rows"])

        # 2) profile
        rp = client.get(f"/api/v1/datasets/{did}/profile")
        assert rp.status_code == 200, rp.text
        pf = rp.json()["data"]
        assert pf["cols"] == 10
        assert any(f["inferred_type"] == "numeric" for f in pf["fields"])
        print("profile 200, fields:", len(pf["fields"]))

        # 3) quality
        rq = client.get(f"/api/v1/datasets/{did}/quality")
        assert rq.status_code == 200, rq.text
        q = rq.json()["data"]
        assert q["duplicate_rows"] == 1
        print("quality 200, score:", q["score"], "issues:", len(q["issues"]))

        # 4) 404
        r404 = client.get("/api/v1/datasets/nope/profile")
        assert r404.status_code == 404
        print("404 路径 OK")

        # 5) 超大文件
        big = ("a,b\n" + "".join(f"{i},{i*2}\n" for i in range(60000))).encode()
        rb = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("big.csv", big, "text/csv")},
        )
        assert rb.status_code == 200 and "采样" in (rb.json()["data"]["note"] or "")
        print("大文件采样 OK")

    print("\nALL_HTTP_TESTS_PASSED")


if __name__ == "__main__":
    test_main()
