"""
AI Teaching Copilot — Gradio Web UI

启动方式:
    uv run python webui.py
    uv run python webui.py --share  （生成公网链接）
"""

import os
import json
import argparse
import tempfile
from datetime import datetime
from pathlib import Path

# Load .env before anything else
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value

import gradio as gr

from app import run_workflow, export_outputs
from cache import clear_cache, cache_stats, list_cached, delete_cached, get_cached, get_cache_key, set_cached
from models.runtime import TeacherRuntimePlan, ClassroomSection, HomeworkTask
from renderers.markdown_renderer import render_markdown
from compiler.pedagogical_compiler import score_runtime_plan


# ─── 共享状态 ────────────────────────────────────────────────

def _now_iso():
    return datetime.now().isoformat()


def _plan_to_display_data(result: dict) -> dict:
    """从 run_workflow 结果中提取用于展示的数据"""
    runtime_data = result.get("teacher_runtime_plan")
    if not runtime_data:
        return {"md": "无教案数据", "plan_dict": None, "status": "无数据"}

    plan = TeacherRuntimePlan.model_validate(runtime_data)
    md = render_markdown(plan)
    quality = score_runtime_plan(plan)
    stats = result.get("statistics", {})
    status = (
        f"质量评分: {quality['total']}/{quality['max']} ({quality['grade']}) | "
        f"环节: {stats.get('total_sections', 0)} | "
        f"互动: {stats.get('total_interactions', 0)} | "
        f"练习: {stats.get('total_questions', 0)}"
    )
    return {"md": md, "plan_dict": runtime_data, "status": status}


# ─── Tab 1: 生成教案 ─────────────────────────────────────────

def generate_lesson_plan(topic, grade, provider, export_formats):
    if not topic.strip():
        return "请输入教学主题", "错误：主题为空", None, None, None, gr.update()
    if not grade.strip():
        return "请输入年级", "错误：年级为空", None, None, None, gr.update()

    result = run_workflow(topic.strip(), grade.strip(), provider)
    if "error" in result:
        return f"生成失败：{result['error']}", "错误", None, None, None, gr.update()

    display = _plan_to_display_data(result)

    # 导出文件
    output_dir = tempfile.mkdtemp(prefix="lesson_plan_")
    formats_to_export = [f.strip() for f in export_formats if f.strip()]
    exported = export_outputs(result, output_dir, formats_to_export, topic)

    # 更新历史列表
    history_data = _build_history_table()

    return (
        display["md"],
        display["status"],
        exported.get("json"),
        exported.get("md"),
        exported.get("docx"),
        history_data,
    )


# ─── Tab 2: 历史教案 ─────────────────────────────────────────

_HISTORY_COLUMNS = ["key", "主题", "年级", "提供商", "生成时间", "大小(KB)"]


def _build_history_table():
    """构建历史教案表格数据"""
    entries = list_cached()
    if not entries:
        return []
    return [
        [e["key"], e["topic"], e["grade"], e["provider"],
         e["generated_at"][:19].replace("T", " "), e["size_kb"]]
        for e in entries
    ]


def load_history_item(evt: gr.SelectData):
    """点击历史表格中的一行，加载教案"""
    if evt.index[0] is None:
        return "请选择一个教案", "", None, None

    # 获取选中行的 key
    # evt.data 是选中行的数据
    row = evt.data
    if not row:
        return "请选择一个教案", "", None, None

    key = row[0]  # 第一列是 key
    cached = get_cached(key)
    if not cached:
        return "缓存已失效", "", None, None

    display = _plan_to_display_data(cached)
    return display["md"], display["status"], cached, display["plan_dict"]


def delete_history_item(current_state):
    """删除当前查看的历史教案"""
    if not current_state:
        return "请先选择一个教案", _build_history_table()

    meta = current_state.get("metadata", {})
    topic = meta.get("topic", "")
    grade = meta.get("grade", "")
    provider = meta.get("llm_provider", "")

    key = get_cache_key(topic, grade, provider)
    if delete_cached(key):
        return f"已删除: {topic}", _build_history_table()
    return "删除失败", _build_history_table()


# ─── Tab 3: 编辑教案 ─────────────────────────────────────────

def load_plan_for_edit(plan_dict):
    """将教案数据加载到编辑界面"""
    if not plan_dict:
        return ("",) * 8  # 空值

    plan = TeacherRuntimePlan.model_validate(plan_dict)

    objectives = "\n".join(plan.teaching_objectives)
    summary = plan.summary

    # 课堂环节
    sections_text = ""
    for i, s in enumerate(plan.sections, 1):
        sections_text += f"【环节{i}: {s.title}】\n"
        sections_text += f"时长: {s.duration_minutes or 0}分钟\n"
        sections_text += f"教师活动: {s.teacher_activity}\n"
        sections_text += f"学生活动: {s.student_activity}\n"
        if s.interaction_method:
            sections_text += f"互动方式: {s.interaction_method}\n"
        sections_text += "\n"

    # 作业
    homework_text = ""
    for hw in plan.homework:
        homework_text += f"[{hw.type}] {hw.content}"
        if hw.purpose:
            homework_text += f" （目的: {hw.purpose}）"
        homework_text += "\n"

    # 互动
    interactions_text = ""
    for i, inter in enumerate(plan.interactions, 1):
        interactions_text += f"【互动{i}】\n"
        interactions_text += f"触发: {inter.trigger}\n"
        interactions_text += f"提问: {inter.teacher_question}\n"
        if inter.expected_responses:
            interactions_text += f"预期回答: {'; '.join(inter.expected_responses)}\n"
        if inter.teacher_followup:
            interactions_text += f"追问: {inter.teacher_followup}\n"
        interactions_text += "\n"

    return objectives, sections_text, homework_text, interactions_text, summary


def _parse_objectives(text: str) -> list:
    """解析教学目标文本为列表"""
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    # 去掉序号前缀
    cleaned = []
    for line in lines:
        if line and line[0].isdigit() and (line[1] in ".、. " or (len(line) > 2 and line[1].isdigit())):
            line = line.lstrip("0123456789.、. ")
        cleaned.append(line)
    return cleaned


def _parse_sections(text: str) -> list:
    """解析课堂环节文本为 ClassroomSection 列表"""
    import re
    sections = []
    blocks = re.split(r"【环节\d+[：:]\s*", text)
    for block in blocks[1:]:  # 跳过第一个空块
        lines = block.strip().split("\n")
        title = lines[0].rstrip("】").strip() if lines else "未命名环节"

        fields = {}
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            for prefix, key in [
                ("时长:", "duration"), ("教师活动:", "teacher_activity"),
                ("学生活动:", "student_activity"), ("互动方式:", "interaction_method"),
            ]:
                if line.startswith(prefix):
                    fields[key] = line[len(prefix):].strip()

        duration = None
        if "duration" in fields:
            m = re.search(r"\d+", fields["duration"])
            if m:
                duration = int(m.group())

        sections.append(ClassroomSection(
            title=title,
            teacher_activity=fields.get("teacher_activity", ""),
            student_activity=fields.get("student_activity", ""),
            interaction_method=fields.get("interaction_method", ""),
            duration_minutes=duration,
        ))
    return sections


def _parse_homework(text: str) -> list:
    """解析作业文本为 HomeworkTask 列表"""
    tasks = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # 格式: [必做] 内容 （目的: xxx）
        hw_type = "必做"
        content = line
        purpose = ""
        if line.startswith("["):
            idx = line.find("]")
            if idx > 0:
                hw_type = line[1:idx]
                content = line[idx + 1:].strip()
        if "（目的:" in content:
            parts = content.split("（目的:")
            content = parts[0].strip()
            purpose = parts[1].rstrip("）").strip()
        tasks.append(HomeworkTask(type=hw_type, content=content, purpose=purpose))
    return tasks


def save_edits(
    current_plan_dict, objectives_text, sections_text,
    homework_text, interactions_text, summary_text,
):
    """保存编辑后的教案"""
    if not current_plan_dict:
        return "没有加载教案", "", gr.update()

    plan = TeacherRuntimePlan.model_validate(current_plan_dict)

    # 更新字段
    plan.teaching_objectives = _parse_objectives(objectives_text)
    plan.sections = _parse_sections(sections_text)
    plan.homework = _parse_homework(homework_text)
    plan.summary = summary_text.strip()

    # 更新缓存
    meta = current_plan_dict.get("metadata", {}) if isinstance(current_plan_dict, dict) else {}
    key = get_cache_key(plan.topic, plan.grade, meta.get("llm_provider", "mimo"))

    # 读取原始缓存数据并更新 teacher_runtime_plan
    cached = get_cached(key)
    if cached:
        cached["teacher_runtime_plan"] = plan.model_dump()
        set_cached(key, cached)

    # 重新渲染
    md = render_markdown(plan)
    quality = score_runtime_plan(plan)
    status = f"已保存 | 质量评分: {quality['total']}/{quality['max']} ({quality['grade']})"

    return status, md, plan.model_dump()


# ─── 构建 UI ──────────────────────────────────────────────────

def build_ui():
    with gr.Blocks(title="AI Teaching Copilot") as demo:
        gr.Markdown("# AI Teaching Copilot\n智能教案生成助手")

        # 共享状态
        current_result = gr.State(None)  # 当前教案的完整 result dict
        current_plan_dict = gr.State(None)  # 当前 teacher_runtime_plan dict

        with gr.Tabs():
            # ── Tab 1: 生成教案 ──
            with gr.Tab("生成教案"):
                with gr.Row():
                    with gr.Column(scale=1):
                        topic_input = gr.Textbox(label="教学主题", placeholder="例如：二次函数", lines=1)
                        grade_input = gr.Textbox(label="年级", placeholder="例如：高二", lines=1)
                        provider_input = gr.Dropdown(label="LLM 提供商", choices=["mimo", "claude", "qwen", "longcat"], value="mimo")
                        export_input = gr.CheckboxGroup(label="导出格式", choices=["json", "md", "docx"], value=["json", "md", "docx"])
                        generate_btn = gr.Button("生成教案", variant="primary", size="lg")
                        gen_status = gr.Textbox(label="状态", interactive=False)

                        gr.Markdown("### 下载")
                        json_file = gr.File(label="JSON", interactive=False)
                        md_file = gr.File(label="Markdown", interactive=False)
                        docx_file = gr.File(label="DOCX", interactive=False)

                    with gr.Column(scale=2):
                        gen_output_md = gr.Markdown(label="教案预览", value="*点击「生成教案」开始*")

            # ── Tab 2: 历史教案 ──
            with gr.Tab("历史教案"):
                with gr.Row():
                    with gr.Column(scale=1):
                        history_table = gr.Dataframe(
                            headers=_HISTORY_COLUMNS,
                            datatype=["str", "str", "str", "str", "str", "number"],
                            label="历史教案",
                            interactive=False,
                            value=_build_history_table(),
                        )
                        with gr.Row():
                            refresh_btn = gr.Button("刷新列表", size="sm")
                            delete_btn = gr.Button("删除选中", variant="stop", size="sm")
                        history_status = gr.Textbox(label="操作结果", interactive=False)

                    with gr.Column(scale=2):
                        history_preview = gr.Markdown(label="教案预览", value="*点击左侧列表中的教案查看*")

            # ── Tab 3: 编辑教案 ──
            with gr.Tab("编辑教案"):
                gr.Markdown("*先在「生成教案」或「历史教案」中加载一个教案，再切换到此页面编辑*")
                with gr.Row():
                    with gr.Column(scale=1):
                        load_for_edit_btn = gr.Button("加载当前教案", variant="secondary")

                        edit_objectives = gr.Textbox(label="教学目标（每行一个）", lines=5, placeholder="每行一个教学目标")
                        edit_sections = gr.Textbox(label="课堂环节", lines=12, placeholder="格式：\n【环节1: 标题】\n时长: 10分钟\n教师活动: ...\n学生活动: ...")
                        edit_homework = gr.Textbox(label="作业（每行一条）", lines=4, placeholder="[必做] 内容")
                        edit_interactions = gr.Textbox(label="课堂互动", lines=6, placeholder="【互动1】\n触发: ...\n提问: ...")
                        edit_summary = gr.Textbox(label="课堂小结", lines=3)

                        save_btn = gr.Button("保存编辑", variant="primary")
                        edit_status = gr.Textbox(label="状态", interactive=False)

                    with gr.Column(scale=2):
                        edit_preview = gr.Markdown(label="预览", value="*加载教案后可编辑*")
                        edit_export_btn = gr.Button("导出编辑后版本", variant="secondary")
                        edit_json_file = gr.File(label="导出 JSON", interactive=False)

        # ── 事件绑定 ──

        # Tab 1: 生成
        generate_btn.click(
            fn=generate_lesson_plan,
            inputs=[topic_input, grade_input, provider_input, export_input],
            outputs=[gen_output_md, gen_status, json_file, md_file, docx_file, history_table],
        ).then(
            fn=lambda r: r,
            inputs=[gen_output_md],
            outputs=[gen_output_md],
        )

        # Tab 2: 历史列表交互
        def on_history_select(evt: gr.SelectData):
            row = evt.data
            if not row:
                return "", "", None, None
            key = row[0]
            cached = get_cached(key)
            if not cached:
                return "缓存已失效", "", None, None
            display = _plan_to_display_data(cached)
            return display["md"], display["status"], cached, cached.get("teacher_runtime_plan")

        history_table.select(
            fn=on_history_select,
            outputs=[history_preview, history_status, current_result, current_plan_dict],
        )

        refresh_btn.click(fn=lambda: (_build_history_table(), "已刷新"), outputs=[history_table, history_status])

        def do_delete_history(current_res):
            if not current_res:
                return "请先点击列表中的教案", _build_history_table()
            meta = current_res.get("metadata", {})
            key = get_cache_key(meta.get("topic", ""), meta.get("grade", ""), meta.get("llm_provider", ""))
            if delete_cached(key):
                return f"已删除: {meta.get('topic', '')}", _build_history_table()
            return "删除失败", _build_history_table()

        delete_btn.click(fn=do_delete_history, inputs=[current_result], outputs=[history_status, history_table])

        # Tab 3: 编辑
        load_for_edit_btn.click(
            fn=load_plan_for_edit,
            inputs=[current_plan_dict],
            outputs=[edit_objectives, edit_sections, edit_homework, edit_interactions, edit_summary],
        ).then(
            fn=lambda plan_d: _plan_to_display_data({"teacher_runtime_plan": plan_d})["md"] if plan_d else "请先加载教案",
            inputs=[current_plan_dict],
            outputs=[edit_preview],
        )

        def do_save_edits(plan_d, obj, sec, hw, inter, summ):
            status, md, new_plan = save_edits(plan_d, obj, sec, hw, inter, summ)
            return status, md, new_plan

        save_btn.click(
            fn=do_save_edits,
            inputs=[current_plan_dict, edit_objectives, edit_sections, edit_homework, edit_interactions, edit_summary],
            outputs=[edit_status, edit_preview, current_plan_dict],
        )

        def do_export_edited(plan_d):
            if not plan_d:
                return None
            plan = TeacherRuntimePlan.model_validate(plan_d)
            path = os.path.join(tempfile.mkdtemp(prefix="edit_"), f"{plan.topic}_edited.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(plan_d, f, ensure_ascii=False, indent=2)
            return path

        edit_export_btn.click(fn=do_export_edited, inputs=[current_plan_dict], outputs=[edit_json_file])

    return demo


def main():
    parser = argparse.ArgumentParser(description="AI Teaching Copilot Web UI")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=7860, help="监听端口")
    parser.add_argument("--share", action="store_true", help="生成公网链接")
    args = parser.parse_args()

    demo = build_ui()
    demo.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        theme=gr.themes.Soft(),
    )


if __name__ == "__main__":
    main()
