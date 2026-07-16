"""数据集存储仓库：Parquet 落盘 + SQLite 元数据索引。

设计要点（见产品规划 2.6）：
- 原始/清洗后 DataFrame 以 Parquet 文件存于 data_dir，按 dataset_id 索引，进程重启不丢。
- 不用内存字典：避免重启丢数据、多用户并发吃光内存。
- 接口隔离：未来可换 Railway Volume / S3，只需改本类实现。
"""
import datetime
import os
import sqlite3
import uuid

import pandas as pd


class DatasetRepository:
    def __init__(self, data_dir: str, db_path: str):
        self.data_dir = data_dir
        self.db_path = db_path
        os.makedirs(data_dir, exist_ok=True)

    # ---------- 路径 ----------
    def _path(self, dataset_id: str, suffix: str = "") -> str:
        return os.path.join(self.data_dir, f"{dataset_id}{suffix}.parquet")

    # ---------- 原始数据 ----------
    def save_raw(self, df: pd.DataFrame, filename: str) -> str:
        dataset_id = uuid.uuid4().hex
        path = self._path(dataset_id)
        # 原子写：先写临时文件再 rename
        tmp = path + ".tmp"
        df.to_parquet(tmp, index=False)
        os.replace(tmp, path)
        size_mb = os.path.getsize(path) / (1024 * 1024)
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO datasets VALUES (?,?,?,?,?,?,?)",
            (
                dataset_id,
                filename,
                len(df),
                df.shape[1],
                round(size_mb, 3),
                datetime.datetime.utcnow().isoformat(),
                "ready",
            ),
        )
        conn.commit()
        conn.close()
        return dataset_id

    def load_raw(self, dataset_id: str) -> pd.DataFrame:
        return pd.read_parquet(self._path(dataset_id))

    # ---------- 清洗后数据（保留原始可追溯） ----------
    def save_clean(self, dataset_id: str, df: pd.DataFrame) -> None:
        path = self._path(dataset_id, "_clean")
        tmp = path + ".tmp"
        df.to_parquet(tmp, index=False)
        os.replace(tmp, path)

    def load_clean(self, dataset_id: str) -> pd.DataFrame:
        return pd.read_parquet(self._path(dataset_id, "_clean"))

    # ---------- 元数据 ----------
    def get_metadata(self, dataset_id: str) -> dict | None:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM datasets WHERE id=?", (dataset_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def list_datasets(self) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM datasets ORDER BY created_at DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete(self, dataset_id: str) -> None:
        for suffix in ("", "_clean", "_profile"):
            p = self._path(dataset_id, suffix)
            if os.path.exists(p):
                os.remove(p)
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM datasets WHERE id=?", (dataset_id,))
        conn.commit()
        conn.close()
