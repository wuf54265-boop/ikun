"""依赖注入：配置与存储仓库的单例提供。"""
from fastapi import Depends

from app.config import Settings, get_settings
from app.store.dataset_repo import DatasetRepository


def get_dataset_repo(settings: Settings = Depends(get_settings)) -> DatasetRepository:
    """每次请求注入 DatasetRepository（按 dataset_id 落盘 Parquet + SQLite 元数据）。"""
    return DatasetRepository(data_dir=settings.data_dir, db_path=settings.db_path)
