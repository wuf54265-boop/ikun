"""SQLite 元数据初始化（datasets 表）。仅存路径与摘要，大 DataFrame 不入库。"""
import os
import sqlite3


def init_db(db_path: str) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS datasets (
            id         TEXT PRIMARY KEY,
            filename   TEXT,
            rows       INTEGER,
            cols       INTEGER,
            size_mb    REAL,
            created_at TEXT,
            status     TEXT
        )
        """
    )
    conn.commit()
    conn.close()
