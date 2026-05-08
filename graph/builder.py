"""
LangGraph 工作流构建器

负责创建和管理 AI Teaching Copilot 的 LangGraph 工作流。
"""

import logging
import os
from typing import Callable, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.graph import CompiledGraph

from langgraph.graph import StateGraph, END
from graph.state import TeachingState, NodeNames
from nodes.planner_node import create_planner_node
from nodes.knowledge_node import create_knowledge_node
from nodes.design_node import create_design_node
from nodes.content_node import create_content_node
from nodes.formatter_node import create_formatter_node


logger = logging.getLogger(__name__)


class WorkflowBuilder:
    """
    LangGraph 工作流构建器

    负责：
    - 注册所有节点
    - 配置工作流边
    - 编译和返回可执行的工作流
    - 支持多模型提供商
    """

    def __init__(self, default_provider: str = "claude"):
        self.workflow = None
        self.compiled_graph = None
        self.llm_provider = default_provider

    def set_llm_provider(self, provider: str) -> None:
        """设置 LLM 提供商"""
        self.llm_provider = provider
        logger.info(f"设置 LLM 提供商为: {provider}")

    def build_workflow(self, llm_provider: str = None) -> "CompiledGraph":
        """
        构建完整的 LangGraph 工作流

        Args:
            llm_provider: 可选的 LLM 提供商覆盖

        Returns:
            编译后的工作流图
        """
        # 如果提供了 provider，则使用它覆盖默认值
        if llm_provider is not None:
            self.llm_provider = llm_provider

        logger.info(f"开始构建 LangGraph 工作流 (提供商: {self.llm_provider})")

        # 创建工作流图
        workflow = StateGraph(TeachingState)

        # 注册所有节点
        self._register_nodes(workflow)

        # 配置工作流边
        self._configure_edges(workflow)

        # 编译工作流
        compiled_graph = workflow.compile()

        self.workflow = workflow
        self.compiled_graph = compiled_graph

        logger.info("LangGraph 工作流构建完成")
        return compiled_graph

    def _register_nodes(self, workflow: StateGraph) -> None:
        """注册所有工作流节点"""
        logger.debug("注册工作流节点")

        # 注册 planner 节点
        planner_func = create_planner_node()
        workflow.add_node(NodeNames.PLANNER, planner_func)
        logger.debug(f"已注册 {NodeNames.PLANNER} 节点")

        # 注册 knowledge 节点
        knowledge_func = create_knowledge_node()
        workflow.add_node(NodeNames.KNOWLEDGE, knowledge_func)
        logger.debug(f"已注册 {NodeNames.KNOWLEDGE} 节点")

        # 注册 design 节点
        design_func = create_design_node()
        workflow.add_node(NodeNames.DESIGN, design_func)
        logger.debug(f"已注册 {NodeNames.DESIGN} 节点")

        # 注册 content 节点
        content_func = create_content_node()
        workflow.add_node(NodeNames.CONTENT, content_func)
        logger.debug(f"已注册 {NodeNames.CONTENT} 节点")

        # 注册 formatter 节点
        formatter_func = create_formatter_node()
        workflow.add_node(NodeNames.FORMATTER, formatter_func)
        logger.debug(f"已注册 {NodeNames.FORMATTER} 节点")

        # 环境变量仅在未显式指定 provider 时作为 fallback
        if self.llm_provider is None:
            self.llm_provider = os.getenv("LLM_PROVIDER", "claude")
        logger.info(f"使用 LLM 提供商: {self.llm_provider}")

    def _configure_edges(self, workflow: StateGraph) -> None:
        """配置工作流边"""
        logger.debug("配置工作流边")

        # 设置开始节点
        workflow.set_entry_point(NodeNames.PLANNER)
        logger.debug(f"设置入口点为 {NodeNames.PLANNER}")

        # 配置节点间的边
        edges = [
            (NodeNames.PLANNER, NodeNames.KNOWLEDGE),
            (NodeNames.KNOWLEDGE, NodeNames.DESIGN),
            (NodeNames.DESIGN, NodeNames.CONTENT),
            (NodeNames.CONTENT, NodeNames.FORMATTER),
            (NodeNames.FORMATTER, END)
        ]

        for from_node, to_node in edges:
            workflow.add_edge(from_node, to_node)
            logger.debug(f"添加边: {from_node} -> {to_node}")

        # 添加条件边（如果需要的话）
        # 目前使用简单的线性流程，所以不需要条件边

        logger.debug("工作流边配置完成")


# 全局工作流构建器实例
_workflow_builder_instance = None


def get_workflow_builder(llm_provider: str = None) -> WorkflowBuilder:
    """获取全局工作流构建器实例"""
    global _workflow_builder_instance

    # 如果提供了 provider 并且 builder 不存在，则使用它
    if llm_provider is not None and _workflow_builder_instance is None:
        _workflow_builder_instance = WorkflowBuilder(default_provider=llm_provider)

    # 如果 builder 不存在，创建默认的
    if _workflow_builder_instance is None:
        _workflow_builder_instance = WorkflowBuilder()

    # 如果提供了 provider，更新已存在的 builder
    if llm_provider is not None:
        _workflow_builder_instance.set_llm_provider(llm_provider)

    return _workflow_builder_instance


def build_teaching_copilot_graph(llm_provider: str = None) -> "CompiledGraph":
    """
    构建 AI Teaching Copilot 的主工作流

    Args:
        llm_provider: 可选的 LLM 提供商覆盖

    Returns:
        编译后的 LangGraph 工作流
    """
    builder = get_workflow_builder()
    return builder.build_workflow(llm_provider)


# 预编译的工作流（在导入时自动构建）
try:
    TEACHING_COPILOT_GRAPH: "CompiledGraph" = build_teaching_copilot_graph()
    logger.info("AI Teaching Copilot 工作流预编译完成")
except Exception as e:
    logger.error(f"工作流预编译失败: {e}")
    TEACHING_COPILOT_GRAPH = None