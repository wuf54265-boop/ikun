"""应用配置（环境变量驱动，开发/生产共用一份）。"""
from functools import lru_cache

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
    cors_origins: list[str] = ["http://localhost:3000"]

    # AI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # 采样（超大文件）
    sample_rows: int = 50000


@lru_cache
def get_settings() -> Settings:
    return Settings()
