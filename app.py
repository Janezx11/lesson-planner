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

from utils.env import load_dotenv
load_dotenv()

from graph.state import create_initial_state, TeachingState
from graph.builder import build_teaching_copilot_graph
from cache import get_cache_key, get_cached, set_cached, clear_cache, cache_stats


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


def run_workflow(
    topic: str,
    grade: str,
    provider: str = "claude",
    duration: str = "45分钟",
    level: str = "普通",
    use_cache: bool = True,
    unit_context: str = "",
) -> Dict[str, Any]:
    """
    运行完整的教学方案设计工作流

    Args:
        topic: 教学主题
        grade: 年级
        provider: LLM 提供商
        duration: 课时时长（如 40分钟、45分钟、90分钟）
        level: 班级水平（快班、普通、基础）
        use_cache: 是否使用缓存
        unit_context: 单元上下文（多课时生成时注入）

    Returns:
        最终的教学方案字典
    """
    logger.info(f"开始执行教学方案设计: 主题={topic}, 年级={grade}, 提供商={provider}, 时长={duration}, 水平={level}")

    # 检查缓存（key 包含 duration 和 level）
    if use_cache and not unit_context:
        cache_key = get_cache_key(topic, grade, provider, duration, level)
        cached = get_cached(cache_key)
        if cached is not None:
            cached.setdefault("metadata", {})["generated_at"] = datetime.now().isoformat()
            logger.info("使用缓存结果")
            return cached

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
    initial_state = create_initial_state(topic, grade, provider, duration, level, unit_context)

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
                "duration": duration,
                "level": level,
                "version": "5.0",
                "llm_provider": provider,
                "errors_encountered": error_count
            },
            **final_output
        }

        # 写入缓存
        if use_cache:
            set_cached(cache_key, enriched_output)

        logger.info("教学方案设计完成")
        return enriched_output

    except Exception as e:
        logger.error(f"工作流执行失败: {e}")
        return {"error": f"工作流执行失败: {str(e)}"}


def run_unit_workflow(
    topic: str,
    grade: str,
    total_lessons: int,
    provider: str = "mimo",
    duration: str = "45分钟",
    level: str = "普通",
) -> Dict[str, Any]:
    """运行单元计划工作流：先生成单元规划，再逐课时生成教案。

    Args:
        topic: 教学主题
        grade: 年级
        total_lessons: 总课时数
        provider: LLM 提供商
        duration: 每课时时长
        level: 班级水平

    Returns:
        包含 unit_plan 和 lessons 的字典
    """
    from llm.factory import get_llm_for_state
    from compiler.unit_compiler import generate_unit_plan, build_lesson_context, validate_unit_coherence
    from models.runtime import TeacherRuntimePlan

    logger.info(f"开始单元计划工作流: 主题={topic}, 课时数={total_lessons}")

    os.environ["LLM_PROVIDER"] = provider
    llm_client = get_llm_for_state({"provider": provider})

    # Step 1: 生成单元计划
    try:
        unit_plan = generate_unit_plan(topic, grade, total_lessons, duration, level, llm_client)
    except Exception as e:
        logger.error(f"单元计划生成失败: {e}")
        return {"error": f"单元计划生成失败: {str(e)}"}

    # Step 2: 逐课时生成教案
    lessons = []
    previous_summary = None

    for lesson_outline in unit_plan.lessons:
        lesson_number = lesson_outline.lesson_number
        logger.info(f"生成第 {lesson_number}/{total_lessons} 课时: {lesson_outline.title}")

        # 构建单元上下文
        unit_context = build_lesson_context(unit_plan, lesson_outline, previous_summary)

        # 生成单课时教案
        lesson_topic = f"{topic} - {lesson_outline.title}"
        result = run_workflow(
            topic=lesson_topic,
            grade=grade,
            provider=provider,
            duration=lesson_outline.duration or duration,
            level=level,
            use_cache=False,
            unit_context=unit_context,
        )

        if "error" in result:
            logger.warning(f"第 {lesson_number} 课时生成失败: {result['error']}")
            lessons.append({"error": result["error"], "lesson_number": lesson_number})
        else:
            lessons.append(result)
            # 提取本课时小结，用于下一课时的上下文
            runtime_data = result.get("teacher_runtime_plan", {})
            if runtime_data:
                previous_summary = runtime_data.get("summary", "")

    # Step 3: 校验连贯性
    valid_lessons = []
    for l in lessons:
        if "error" not in l:
            runtime_data = l.get("teacher_runtime_plan", {})
            if runtime_data:
                try:
                    valid_lessons.append(TeacherRuntimePlan.model_validate(runtime_data))
                except Exception:
                    pass

    coherence_issues = []
    if len(valid_lessons) > 1:
        coherence_issues = validate_unit_coherence(unit_plan, valid_lessons)
        if coherence_issues:
            logger.warning(f"单元连贯性校验发现问题: {coherence_issues}")

    return {
        "unit_plan": unit_plan.model_dump(),
        "lessons": lessons,
        "coherence_issues": coherence_issues,
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "topic": topic,
            "grade": grade,
            "total_lessons": total_lessons,
            "provider": provider,
            "duration": duration,
            "level": level,
        },
    }


def export_outputs(
    result: Dict[str, Any],
    output_dir: str,
    formats: list,
    topic: str,
) -> Dict[str, str]:
    """
    将结果导出为多种格式。

    Args:
        result: 工作流结果
        output_dir: 输出目录
        formats: 导出格式列表 (json, md, docx)
        topic: 教学主题（用于文件名）

    Returns:
        导出文件路径字典
    """
    from models.runtime import TeacherRuntimePlan
    from exporters import export_to_docx, export_to_markdown

    # 创建输出目录
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 生成文件名前缀
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 清理主题名用于文件名
    safe_topic = "".join(c for c in topic if c.isalnum() or c in "_ -")[:20]
    prefix = f"{safe_topic}_{timestamp}" if safe_topic else f"lesson_plan_{timestamp}"

    exported = {}

    # 解析 TeacherRuntimePlan
    runtime_data = result.get("teacher_runtime_plan")
    runtime_plan = None
    if runtime_data:
        try:
            runtime_plan = TeacherRuntimePlan.model_validate(runtime_data)
        except Exception as e:
            logger.warning(f"无法解析 TeacherRuntimePlan: {e}")

    for fmt in formats:
        try:
            if fmt == "json":
                path = os.path.join(output_dir, f"{prefix}.json")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                exported["json"] = path
                logger.info(f"JSON 已导出: {path}")

            elif fmt == "md" and runtime_plan:
                path = os.path.join(output_dir, f"{prefix}.md")
                export_to_markdown(runtime_plan, path)
                exported["md"] = path
                logger.info(f"Markdown 已导出: {path}")

            elif fmt == "docx" and runtime_plan:
                path = os.path.join(output_dir, f"{prefix}.docx")
                export_to_docx(runtime_plan, path)
                exported["docx"] = path
                logger.info(f"DOCX 已导出: {path}")

            elif fmt in ("md", "docx") and not runtime_plan:
                logger.warning(f"无法导出 {fmt}: TeacherRuntimePlan 数据不可用")

        except Exception as e:
            logger.error(f"导出 {fmt} 失败: {e}")

    return exported


def print_summary(result: Dict[str, Any], exported: Dict[str, str]) -> None:
    """打印结果摘要"""
    if "error" in result:
        print(f"ERROR: {result['error']}")
        return

    metadata = result.get("metadata", {})

    print("-" * 60)
    print("AI Teaching Copilot - 教案生成完成!")
    print("-" * 60)
    print(f"主题: {metadata.get('topic', 'Unknown')}")
    print(f"年级: {metadata.get('grade', 'Unknown')}")
    print(f"生成时间: {metadata.get('generated_at', 'Unknown')}")
    print(f"版本: {metadata.get('version', 'Unknown')}")
    print(f"LLM 提供商: {metadata.get('llm_provider', 'Unknown')}")
    print()

    # 统计信息
    stats = result.get("statistics", {})
    if stats:
        print("统计信息:")
        print(f"  教学环节: {stats.get('total_sections', 0)} 个")
        print(f"  课堂互动: {stats.get('total_interactions', 0)} 个")
        print(f"  练习题: {stats.get('total_questions', 0)} 道")
        print(f"  作业: {stats.get('total_homework', 0)} 项")
        print()

    # 导出文件
    if exported:
        print("导出文件:")
        for fmt, path in exported.items():
            print(f"  {fmt.upper()}: {path}")
        print()

    print("生成完成!")
    print("-" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="AI Teaching Copilot - 智能教学助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python app.py --topic "二次函数" --grade "高中二年级"
  python app.py --topic "英语的现在进行时" --grade "初中一年级" --export docx
  python app.py --topic "网络分层" --grade "职高" --export all --output-dir outputs
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
        "--export",
        type=str,
        nargs="+",
        choices=["json", "md", "docx", "all"],
        default=["json"],
        help="导出格式 (json, md, docx, all)，默认 json"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="输出目录，默认 outputs/"
    )

    parser.add_argument(
        "--provider",
        type=str,
        default="claude",
        help="LLM 提供商名称。内置: claude, qwen, longcat。"
             "任何 OpenAI 兼容的 provider 可通过 LLMConfig.register_provider() 添加"
    )

    parser.add_argument(
        "--duration",
        type=str,
        default="45分钟",
        help="课时时长（如 40分钟、45分钟、90分钟），默认 45分钟"
    )

    parser.add_argument(
        "--level",
        type=str,
        default="普通",
        choices=["快班", "普通", "基础"],
        help="班级水平：快班、普通、基础，默认 普通"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="启用详细日志输出"
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="跳过缓存，强制重新生成"
    )

    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="清除所有缓存后退出"
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # 清除缓存
    if args.clear_cache:
        count = clear_cache()
        print(f"已清除 {count} 个缓存文件")
        return 0

    # 处理 "all" 格式
    formats = args.export
    if "all" in formats:
        formats = ["json", "md", "docx"]

    logger.info(f"启动 AI Teaching Copilot，主题: {args.topic}，年级: {args.grade}")

    try:
        # 运行工作流
        result = run_workflow(
            args.topic, args.grade, args.provider,
            duration=args.duration, level=args.level,
            use_cache=not args.no_cache,
        )

        if "error" in result:
            print(f"ERROR: {result['error']}")
            return 1

        # 导出文件
        exported = export_outputs(
            result,
            output_dir=args.output_dir,
            formats=formats,
            topic=args.topic,
        )

        # 打印摘要
        print_summary(result, exported)

        return 0

    except KeyboardInterrupt:
        logger.info("用户中断操作")
        print("\n\n操作被用户中断")
        return 1
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        print(f"\nERROR Program execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
