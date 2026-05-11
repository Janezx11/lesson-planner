"""
base_exporter - 导出器基类
"""

from abc import ABC, abstractmethod
from models.runtime import TeacherRuntimePlan


class BaseExporter(ABC):
    """导出器基类"""

    @abstractmethod
    def export(self, plan: TeacherRuntimePlan, output_path: str) -> str:
        """
        将 TeacherRuntimePlan 导出为文件。

        Args:
            plan: 教师运行时教案
            output_path: 输出文件路径

        Returns:
            实际写入的文件路径
        """
        pass
