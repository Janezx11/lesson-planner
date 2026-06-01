"""环境变量加载工具"""

import os


def load_dotenv(path: str = ".env") -> None:
    """从 .env 文件加载环境变量到 os.environ。

    已存在的环境变量不会被覆盖（系统环境变量优先）。
    """
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key and key not in os.environ:
                os.environ[key] = value.strip()
