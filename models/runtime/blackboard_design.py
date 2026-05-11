"""
BlackboardDesign - 板书设计模型
"""

from typing import List
from pydantic import BaseModel, Field


class BlackboardDesign(BaseModel):
    """板书设计"""

    layout: str = Field(default="", description="布局描述")
    main_content: List[str] = Field(default_factory=list, description="主板书内容")
    key_formulas: List[str] = Field(default_factory=list, description="核心公式/概念")
    diagrams: List[str] = Field(default_factory=list, description="图示说明")
