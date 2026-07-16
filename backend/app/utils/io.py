"""文件读取工具：CSV/Excel -> DataFrame，编码自动探测链。

探测顺序（中文常见场景优先，latin-1 作为最后兜底，保证任何字节流都能 decode 不崩）：
utf-8 -> gbk -> gb2312 -> gb18030 -> latin-1
"""
from __future__ import annotations

import io as _io

import pandas as pd

_ENCODINGS = ["utf-8", "gbk", "gb2312", "gb18030", "latin-1"]


def read_table_file(raw: bytes, filename: str) -> pd.DataFrame:
    """上传字节流解析为 DataFrame。

    异常语义：
    - 空字节流 -> ValueError("空文件")
    - Excel 直接走 pd.read_excel
    - CSV 依次尝试编码链；全部失败抛 ValueError 并附带最后错误
    """
    if not raw or len(raw) == 0:
        raise ValueError("空文件：未读取到任何字节内容")

    if filename.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(_io.BytesIO(raw))

    last_err: Exception | None = None
    for enc in _ENCODINGS:
        try:
            df = pd.read_csv(_io.BytesIO(raw), encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            # 编码不匹配，试下一个
            last_err = None
            continue
        except pd.errors.EmptyDataError:
            raise ValueError("空文件：CSV 解析后无有效数据行")
        except Exception as e:  # 其他解析错误（分隔符、损坏等）
            last_err = e
            continue

        if df.empty:
            raise ValueError("空文件：CSV 解析后仅有表头或无数据行")
        return df

    raise ValueError(f"无法解析 CSV（已尝试编码 {_ENCODINGS}）：{last_err}")
