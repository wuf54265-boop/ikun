"""应用配置（环境变量驱动，开发/生产共用一份）。"""
from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # 基础
    app_name: str = "AI 数据分析助手"
    env: str = "development"
    api_v1_prefix: str = "/api/v1"

    # 存储（文件系统 Parquet + SQLite 元数据，绝不用内存字典）
    data_dir: str = "./data"
    db_path: str = "./data/meta.db"

    # 上传限制
    max_upload_mb: int = 50

    # CORS（前端开发地址）
    # 声明为 Any 以跳过 pydantic-settings 对 list 字段的强制 JSON 解析，
    # 再用 before-validator 把「裸 origin / 逗号分隔 / JSON 数组」统一成 list[str]。
    # Railway/Vercel 控制台填逗号分隔最方便，例如：
    #   CORS_ORIGINS=https://xxx.vercel.app,http://localhost:3000
    cors_origins: Any = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json
                return json.loads(v)
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    # AI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # 采样（超大文件）
    sample_rows: int = 50000


@lru_cache
def get_settings() -> Settings:
    return Settings()
