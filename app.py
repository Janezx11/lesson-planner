#!/usr/bin/env python3
"""
AI Teaching Copilot（智能教学助手）主应用入口

这个脚本提供了命令行接口来运行 AI Teaching Copilot 工作流。
"""

import argparse
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# Load environment variables from .env file
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

from graph.state import create_initial_state, TeachingState
from graph.builder import build_teaching_copilot_graph
from utils.parser import merge_dicts_safe


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('teaching_copilot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_workflow(topic: str, grade: str, provider: str = "claude") -> Dict[str, Any]:
    """
    运行完整的教学方案设计工作流

    Args:
        topic: 教学主题
        grade: 年级
        provider: LLM 提供商 (claude, qwen, longcat)

    Returns:
        最终的教学方案字典
    """
    logger.info(f"开始执行教学方案设计: 主题={topic}, 年级={grade}, 提供商={provider}")

    # 设置 LLM 提供商
    os.environ["LLM_PROVIDER"] = provider

    # 创建工作流
    try:
        graph = build_teaching_copilot_graph(provider)
        if graph is None:
            raise RuntimeError("无法创建工作流图")
    except Exception as e:
        logger.error(f"创建工作流失败: {e}")
        return {"error": f"创建工作流失败: {str(e)}"}

    # 创建初始状态
    initial_state = create_initial_state(topic, grade, provider)

    # 运行工作流
    try:
        logger.info("启动 LangGraph 工作流...")
        result_state: TeachingState = graph.invoke(initial_state)

        # 获取最终输出
        final_output = result_state.get("final_output", {})
        error_count = result_state.get("error_count", 0)

        if error_count > 0:
            logger.warning(f"工作流完成，但有 {error_count} 个错误发生")

        # 添加元信息
        enriched_output = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "topic": topic,
                "grade": grade,
                "version": "1.0.0",
                "llm_provider": provider,
                "total_duration": "待定",
                "errors_encountered": error_count
            },
            **final_output
        }

        logger.info("教学方案设计完成")
        return enriched_output

    except Exception as e:
        logger.error(f"工作流执行失败: {e}")
        return {"error": f"工作流执行失败: {str(e)}"}


def save_to_file(data: Dict[str, Any], filename: Optional[str] = None) -> str:
    """
    将结果保存到文件

    Args:
        data: 要保存的数据
        filename: 文件名（可选）

    Returns:
        保存的文件路径
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"teaching_plan_{timestamp}.json"

    file_path = Path(filename)

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"结果已保存到: {file_path}")
        return str(file_path)
    except Exception as e:
        logger.error(f"保存文件失败: {e}")
        raise


def print_summary(result: Dict[str, Any]) -> None:
    """
    打印结果的摘要信息

    Args:
        result: 工作流结果
    """
    if "error" in result:
        print(f"ERROR: {result['error']}")
        return

    metadata = result.get("metadata", {})
    executive_summary = result.get("executive_summary", {})

    print("-" * 60)
    print("AI Teaching Copilot - Lesson Plan Generation Complete!")
    print("-" * 60)
    print(f"Topic: {metadata.get('topic', 'Unknown')}")
    print(f"Grade: {metadata.get('grade', 'Unknown')}")
    print(f"Generated at: {metadata.get('generated_at', 'Unknown')}")
    print(f"Version: {metadata.get('version', 'Unknown')}")
    print()

    overview = executive_summary.get("overview", "")
    key_objectives = executive_summary.get("key_objectives", [])

    print("Overall Overview:")
    if overview:
        print(f"   {overview}")
    print()

    if key_objectives:
        print("Core Objectives:")
        for i, objective in enumerate(key_objectives, 1):
            print(f"   {i}. {objective}")
        print()

    learning_objectives = result.get("detailed_plan", {}).get("learning_objectives", {})
    if learning_objectives:
        print("Learning Objectives:")
        for category, objectives in learning_objectives.items():
            if objectives:
                print(f"   {category.title()}:")
                for obj in objectives[:2]:  # Show only first two
                    print(f"     • {obj}")
        print()

    teaching_sequence = result.get("detailed_plan", {}).get("teaching_sequence", [])
    if teaching_sequence:
        print("Teaching Sequence:")
        for i, phase in enumerate(teaching_sequence[:3], 1):  # Show only first three phases
            duration = phase.get("duration", "TBD")
            activities = phase.get("activities", [])
            print(f"   {i}. {phase.get('phase', 'Unknown')} ({duration})")
            for j, activity in enumerate(activities[:2], 1):  # Each phase shows first two activities
                print(f"      {j}. {activity}")
        print()

    resources = result.get("resources", {})
    materials = resources.get("materials", [])
    if materials:
        print("Required Materials:")
        for material in materials[:3]:  # Show only first three
            print(f"   • {material}")
        print()

    print("Generation Complete! Check the full JSON file for detailed plan.")
    print("-" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="AI Teaching Copilot - 智能教学助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python app.py --topic "二次函数" --grade "高中二年级"
  python app.py --topic "牛顿第二定律" --grade "高一物理"
  python app.py --topic "细胞分裂" --grade "初中生物" --output "my_lesson.json"
        """
    )

    parser.add_argument(
        "--topic",
        type=str,
        required=True,
        help="教学主题（例如：二次函数、牛顿第二定律等）"
    )

    parser.add_argument(
        "--grade",
        type=str,
        required=True,
        help="年级（例如：高中二年级、高一物理、初中生物等）"
    )

    parser.add_argument(
        "--output",
        type=str,
        help="输出文件名（可选，默认自动生成）"
    )

    parser.add_argument(
        "--provider",
        type=str,
        choices=["claude", "qwen", "longcat"],
        default="claude",
        help="LLM 提供商 (claude, qwen, longcat)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="启用详细日志输出"
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    logger.info(f"启动 AI Teaching Copilot，主题: {args.topic}，年级: {args.grade}")

    try:
        # 运行工作流
        result = run_workflow(args.topic, args.grade, args.provider)

        # 保存结果
        output_file = save_to_file(result, args.output)

        # 打印摘要
        print_summary(result)

        if "error" not in result:
            print(f"\n💾 详细方案已保存到: {output_file}")
            print("\n🚀 现在你可以：")
            print("   • 使用文本编辑器查看完整的教学方案")
            print("   • 根据方案准备课堂教学材料")
            print("   • 调整方案以适应具体的学生需求")
            print("   • 将方案分享给其他教师参考")

        return 0 if "error" not in result else 1

    except KeyboardInterrupt:
        logger.info("用户中断操作")
        print("\n\n⚠️  操作被用户中断")
        return 1
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        print(f"\nERROR Program execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())