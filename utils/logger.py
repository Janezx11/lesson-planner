"""
统一日志工具模块

提供标准化的 logger 获取方式，确保整个项目使用一致的 logging 配置。
"""

import logging


def get_logger(name: str):
    """
    获取标准化的 logger 实例

    Args:
        name: logger 名称（通常使用 __name__）

    Returns:
        配置好的 logger 实例
    """
    return logging.getLogger(name)


# 预配置的 logger 实例
logger = get_logger(__name__)

# 设置默认的 logging 配置（如果尚未配置）
if not logging.root.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )