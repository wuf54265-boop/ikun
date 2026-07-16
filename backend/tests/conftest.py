"""pytest 公共前置：把存储层指向临时目录。

- 避免测试在仓库根目录创建 ./data / meta.db，污染项目与本地环境；
- conftest 在任意测试模块之前被导入，且此处只设置环境变量、不调用 get_settings()，
  因此 app.main 首次导入时 get_settings()（lru_cache）会读到本临时目录，行为可复现。
"""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="ada_test_")
os.environ["DATA_DIR"] = _TMP
os.environ["DB_PATH"] = os.path.join(_TMP, "meta.db")
