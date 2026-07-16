"""Step 3 集成校验：直接调用 service 层验证 接入→画像→质量 全链路 + 大文件采样。

不依赖 HTTP，运行快；可用于本地冒烟与回归。
"""
from __future__ import annotations

import asyncio
import os
import tempfile

import pandas as pd

from app.config import Settings, get_settings
from app.services import ingestion, profiling
from app.store.db import init_db
from app.store.dataset_repo import DatasetRepository

SAMPLE = os.path.join(os.path.dirname(__file__), "sample.csv")


def make_repo() -> DatasetRepository:
    tmp = tempfile.mkdtemp(prefix="ada_test_")
    db = os.path.join(tmp, "meta.db")
    init_db(db)  # 等效于 app 启动生命周期里做的建表
    repo = DatasetRepository(data_dir=tmp, db_path=db)
    return repo


def test_small():
    repo = make_repo()
    raw = open(SAMPLE, "rb").read()
    res = asyncio.run(ingestion.ingest(raw, "sample.csv", repo))
    assert res.rows == 11, res.rows
    assert res.cols == 10, res.cols
    types = {c.name: c.inferred_type for c in res.columns}
    print("推断类型:", types)
    assert types["amount"] == "numeric"
    assert types["category"] == "categorical"
    assert types["is_member"] == "boolean"
    assert types["order_date"] == "datetime"
    assert types["channel"] == "categorical"  # 常量但归类为 categorical
    assert res.note is None

    df = repo.load_raw(res.dataset_id)
    prof = profiling.profile_dataset(df, res.dataset_id)
    f = {x.name: x for x in prof.fields}
    assert f["amount"].mean is not None
    assert f["amount"].histogram and len(f["amount"].histogram) == 10
    assert f["category"].top_values

    q = profiling.quality_report(df, res.dataset_id)
    print("质量评分:", q.score, "重复行:", q.duplicate_rows, "问题数:", len(q.issues))
    assert q.duplicate_rows == 1
    types_seen = {i.type for i in q.issues}
    assert "duplicate" in types_seen
    assert "missing" in types_seen
    assert "constant" in types_seen
    print("small OK")

    # 高基数 ID 检测：与「重复行」互斥，单独用小样例覆盖
    df_id = pd.DataFrame(
        {"uid": [f"id_{i}" for i in range(20)], "v": list(range(20))}
    )
    q_id = profiling.quality_report(df_id, "syn")
    assert any(i.type == "high_cardinality_id" for i in q_id.issues)
    print("high_cardinality_id OK")


def test_sampling():
    repo = make_repo()
    # 造 60000 行，触发 sample_rows=50000 采样
    n = 60000
    df = pd.DataFrame(
        {
            "x": range(n),
            "y": [i * 1.5 for i in range(n)],
            "g": ["A" if i % 2 == 0 else "B" for i in range(n)],
        }
    )
    raw = df.to_csv(index=False).encode("utf-8")
    res = asyncio.run(ingestion.ingest(raw, "big.csv", repo))
    assert res.rows == n, res.rows
    assert res.note and "采样" in res.note, res.note
    assert len(res.preview) == 20
    print("采样 note:", res.note)
    print("sampling OK")


def test_encoding_gbk():
    repo = make_repo()
    # GBK 编码中文 CSV
    content = "姓名,年龄\n张三,28\n李四,35\n"
    raw = content.encode("gbk")
    res = asyncio.run(ingestion.ingest(raw, "gbk.csv", repo))
    assert res.rows == 2
    print("gbk 编码 OK, 列:", [c.name for c in res.columns])


if __name__ == "__main__":
    # 临时把 data_dir 指到系统临时目录，避免污染项目 ./data
    test_small()
    test_sampling()
    test_encoding_gbk()
    print("\nALL_STEP3_TESTS_PASSED")
