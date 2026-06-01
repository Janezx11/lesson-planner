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

from utils.env import load_dotenv
load_dotenv()

import gradio as gr

from app import run_workflow, export_outputs
from cache import clear_cache, cache_stats, list_cached, delete_cached, get_cached, get_cache_key, set_cached, get_plans_dir, add_reflection, list_reflections
from models.runtime import TeacherRuntimePlan, ClassroomSection, HomeworkTask
from renderers.markdown_renderer import render_markdown
from compiler.pedagogical_compiler import score_runtime_plan, improve_existing_plan, regenerate_section
from llm.factory import get_llm_for_state


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

def generate_lesson_plan(topic, grade, provider, duration, level, export_formats):
    if not topic.strip():
        return "请输入教学主题", "错误：主题为空", None, None, None, gr.update()
    if not grade.strip():
        return "请输入年级", "错误：年级为空", None, None, None, gr.update()

    result = run_workflow(topic.strip(), grade.strip(), provider, duration=duration, level=level)
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


# ─── 常见指令模板 ─────────────────────────────────────────────

_INSTRUCTION_PRESETS = [
    ("增加课堂互动", "增加课堂互动环节，多设计提问和讨论"),
    ("提高练习难度", "练习题太简单，提高难度，增加拓展题"),
    ("增加生活案例", "增加与学生日常生活相关的案例和情境"),
    ("简化内容", "内容过多，精简教师活动，突出重点"),
    ("增加小组讨论", "增加小组合作探究环节，让学生多动手"),
    ("调整时间分配", "调整各环节时间分配，重点环节给更多时间"),
]

_REGEN_PRESETS = [
    ("增加互动", "在这个环节中增加师生互动和提问"),
    ("简化活动", "简化教师活动，突出核心讲解"),
    ("增加学生参与", "增加学生动手/讨论/展示的活动"),
    ("缩短时长", "精简内容，缩短这个环节的时间"),
]


# ─── 自定义 CSS ────────────────────────────────────────────────

_CUSTOM_CSS = """
/* 标题区域 */
.app-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 100%);
    color: white;
    padding: 24px 32px;
    border-radius: 12px;
    margin-bottom: 20px;
}
.app-header h1 {
    color: white !important;
    font-size: 1.8em !important;
    margin: 0 0 4px 0 !important;
}
.app-header p {
    color: rgba(255,255,255,0.85) !important;
    margin: 0 !important;
    font-size: 0.95em;
}

/* Tab 栏 */
.tabs > .tab-nav {
    border-bottom: 2px solid #e2e8f0;
}
.tabs > .tab-nav > button.selected {
    border-bottom: 3px solid #2d6a9f !important;
    color: #1e3a5f !important;
    font-weight: 600;
}

/* 预览区 */
.preview-box {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 16px;
    background: #fafbfc;
    min-height: 400px;
}

/* 状态标签 */
.status-ok {
    background: #d4edda;
    color: #155724;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 0.9em;
}
.status-err {
    background: #f8d7da;
    color: #721c24;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 0.9em;
}

/* 按钮 */
.btn-primary {
    background: linear-gradient(135deg, #2d6a9f, #1e3a5f) !important;
    border: none !important;
    transition: box-shadow 0.2s;
}
.btn-primary:hover {
    box-shadow: 0 4px 12px rgba(45,106,159,0.4) !important;
}

/* 快速指令按钮 */
.preset-btn {
    border: 1px solid #d0d7de !important;
    background: white !important;
    transition: all 0.15s;
    font-size: 0.85em !important;
}
.preset-btn:hover {
    border-color: #2d6a9f !important;
    color: #2d6a9f !important;
    background: #f0f7ff !important;
}

/* 下载区卡片 */
.download-card {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 12px;
    margin-top: 8px;
}
"""


# ─── 构建 UI ──────────────────────────────────────────────────

def build_ui():
    custom_theme = gr.themes.Soft(
        primary_hue="blue",
        neutral_hue="slate",
    ).set(
        button_primary_background_fill="linear-gradient(135deg, #2d6a9f, #1e3a5f)",
        button_primary_background_fill_hover="linear-gradient(135deg, #3a7fc4, #2d6a9f)",
        button_primary_border_color="#1e3a5f",
        button_secondary_background_fill="white",
        button_secondary_background_fill_hover="#f0f7ff",
        button_secondary_border_color="#d0d7de",
        button_secondary_border_color_hover="#2d6a9f",
    )

    with gr.Blocks(title="AI Teaching Copilot", css=_CUSTOM_CSS, theme=custom_theme) as demo:
        gr.HTML("""
        <div class="app-header">
            <h1>AI Teaching Copilot</h1>
            <p>智能教案生成助手 — 输入主题，AI 为你设计完整的教学方案</p>
        </div>
        """)

        # 共享状态
        current_result = gr.State(None)  # 当前教案的完整 result dict
        current_plan_dict = gr.State(None)  # 当前 teacher_runtime_plan dict

        with gr.Tabs():
            # ── Tab 1: 生成教案 ──
            with gr.Tab("生成教案"):
                with gr.Row():
                    with gr.Column(scale=1, min_width=320):
                        gr.Markdown("### 基本设置")
                        topic_input = gr.Textbox(label="教学主题", placeholder="例如：二次函数", lines=1)
                        grade_input = gr.Textbox(label="年级", placeholder="例如：高二", lines=1)
                        with gr.Row():
                            provider_input = gr.Dropdown(label="LLM 提供商", choices=["mimo", "claude", "qwen", "longcat"], value="mimo")
                            duration_input = gr.Dropdown(label="课时时长", choices=["40分钟", "45分钟", "90分钟"], value="45分钟")
                        level_input = gr.Dropdown(label="班级水平", choices=["快班", "普通", "基础"], value="普通")
                        export_input = gr.CheckboxGroup(label="导出格式", choices=["json", "md", "docx"], value=["json", "md", "docx"])
                        generate_btn = gr.Button("生成教案", variant="primary", size="lg")
                        gen_status = gr.Textbox(label="状态", interactive=False, show_label=False)

                        with gr.Accordion("下载文件", open=False):
                            json_file = gr.File(label="JSON", interactive=False)
                            md_file = gr.File(label="Markdown", interactive=False)
                            docx_file = gr.File(label="DOCX", interactive=False)

                    with gr.Column(scale=2):
                        gen_output_md = gr.Markdown(label="教案预览", value="*点击「生成教案」开始*")

            # ── Tab 2: 历史教案 ──
            with gr.Tab("历史教案"):
                with gr.Row():
                    with gr.Column(scale=1, min_width=320):
                        gr.Markdown("### 已保存的教案")
                        history_table = gr.Dataframe(
                            headers=_HISTORY_COLUMNS,
                            datatype=["str", "str", "str", "str", "str", "number"],
                            interactive=False,
                            value=_build_history_table(),
                        )
                        with gr.Row():
                            refresh_btn = gr.Button("刷新列表", size="sm")
                            delete_btn = gr.Button("删除选中", variant="stop", size="sm")
                            open_folder_btn = gr.Button("打开文件夹", size="sm")
                        history_status = gr.Textbox(label="操作结果", interactive=False, show_label=False)

                        with gr.Accordion("课后反思", open=False):
                            gr.Markdown("*上完课后记录教学效果，系统会在下次生成时参考*")
                            ref_what_worked = gr.Textbox(label="效果好的环节", lines=2, placeholder="例如：小组讨论环节学生参与度很高")
                            ref_what_failed = gr.Textbox(label="效果差的环节", lines=2, placeholder="例如：导入环节学生注意力不集中")
                            ref_student_reaction = gr.Textbox(label="学生整体反应", lines=2, placeholder="例如：对实际案例很感兴趣")
                            ref_next_adjustment = gr.Textbox(label="下次调整建议", lines=2, placeholder="例如：增加动手实验环节")
                            save_reflection_btn = gr.Button("保存反思", variant="primary", size="sm")
                            reflection_status = gr.Textbox(label="状态", interactive=False, show_label=False)

                    with gr.Column(scale=2):
                        history_preview = gr.Markdown(label="教案预览", value="*点击左侧列表中的教案查看*")

            # ── Tab 3: 编辑教案 ──
            with gr.Tab("编辑教案"):
                with gr.Row():
                    with gr.Column(scale=1, min_width=320):
                        load_for_edit_btn = gr.Button("加载当前教案", variant="secondary")

                        edit_objectives = gr.Textbox(label="教学目标（每行一个）", lines=5, placeholder="每行一个教学目标")
                        edit_sections = gr.Textbox(label="课堂环节", lines=12, placeholder="格式：\n【环节1: 标题】\n时长: 10分钟\n教师活动: ...\n学生活动: ...")
                        edit_homework = gr.Textbox(label="作业（每行一条）", lines=4, placeholder="[必做] 内容")
                        edit_interactions = gr.Textbox(label="课堂互动", lines=6, placeholder="【互动1】\n触发: ...\n提问: ...")
                        edit_summary = gr.Textbox(label="课堂小结", lines=3)

                        with gr.Row():
                            save_btn = gr.Button("保存编辑", variant="primary")
                            edit_export_btn = gr.Button("导出 JSON", variant="secondary")
                        edit_status = gr.Textbox(label="状态", interactive=False, show_label=False)

                        with gr.Accordion("局部重新生成", open=False):
                            regen_section_idx = gr.Dropdown(label="选择环节", choices=[], interactive=True, info="加载教案后自动填充")
                            regen_provider = gr.Dropdown(label="LLM 提供商", choices=["mimo", "claude", "qwen", "longcat"], value="mimo")
                            regen_instructions = gr.Textbox(label="改进指令", placeholder="例如：增加小组讨论环节、简化教师活动", lines=2)
                            with gr.Row():
                                regen_preset_btns = []
                                for label, text in _REGEN_PRESETS:
                                    btn = gr.Button(value=label, size="sm", variant="secondary")
                                    regen_preset_btns.append((btn, text))
                            regen_btn = gr.Button("重新生成此环节", variant="secondary")
                            regen_status = gr.Textbox(label="状态", interactive=False, show_label=False)

                    with gr.Column(scale=2):
                        edit_preview = gr.Markdown(label="预览", value="*加载教案后可编辑*")
                        edit_json_file = gr.File(label="导出 JSON", interactive=False, visible=False)

            # ── Tab 4: 导入教案 ──
            with gr.Tab("导入教案"):
                with gr.Row():
                    with gr.Column(scale=1, min_width=320):
                        gr.Markdown("### 导入教案")
                        import_json_input = gr.Textbox(label="粘贴教案 JSON", lines=10, placeholder="粘贴完整的教案 JSON 数据...")
                        import_file_input = gr.File(label="或上传 JSON 文件", file_types=[".json"])
                        import_topic = gr.Textbox(label="教学主题", placeholder="例如：二次函数")
                        import_grade = gr.Textbox(label="年级", placeholder="例如：高二")
                        import_provider = gr.Dropdown(label="LLM 提供商", choices=["mimo", "claude", "qwen", "longcat"], value="mimo")
                        import_instructions = gr.Textbox(label="改进指令", lines=2, placeholder="例如：增加互动环节、提高难度")

                        gr.Markdown("**快速指令**")
                        with gr.Row():
                            preset_btns = []
                            for label, text in _INSTRUCTION_PRESETS:
                                btn = gr.Button(value=label, size="sm", variant="secondary")
                                preset_btns.append((btn, text))
                        import_btn = gr.Button("开始改进", variant="primary", size="lg")
                        import_status = gr.Textbox(label="状态", interactive=False, show_label=False)

                        with gr.Accordion("下载文件", open=False):
                            import_json_file = gr.File(label="导出 JSON", interactive=False)
                            import_md_file = gr.File(label="导出 Markdown", interactive=False)
                            import_docx_file = gr.File(label="导出 DOCX", interactive=False)

                    with gr.Column(scale=2):
                        import_preview = gr.Markdown(label="改进后预览", value="*粘贴教案并输入改进指令后点击「开始改进」*")

            # ── Tab 5: 单元计划 ──
            with gr.Tab("单元计划"):
                with gr.Row():
                    with gr.Column(scale=1, min_width=320):
                        gr.Markdown("### 单元设置")
                        unit_topic = gr.Textbox(label="教学主题", placeholder="例如：二次函数")
                        unit_grade = gr.Textbox(label="年级", placeholder="例如：高二")
                        unit_lessons_count = gr.Slider(label="课时数", minimum=2, maximum=8, value=3, step=1)
                        unit_provider = gr.Dropdown(label="LLM 提供商", choices=["mimo", "claude", "qwen", "longcat"], value="mimo")
                        with gr.Row():
                            unit_duration = gr.Dropdown(label="每课时时长", choices=["40分钟", "45分钟", "90分钟"], value="45分钟")
                            unit_level = gr.Dropdown(label="班级水平", choices=["快班", "普通", "基础"], value="普通")
                        unit_btn = gr.Button("生成单元计划", variant="primary", size="lg")
                        unit_status = gr.Textbox(label="状态", interactive=False, show_label=False)

                    with gr.Column(scale=2):
                        unit_plan_preview = gr.Markdown(label="单元规划", value="*输入主题和课时数后点击「生成单元计划」*")

        # ── 事件绑定 ──

        # Tab 1: 生成
        generate_btn.click(
            fn=generate_lesson_plan,
            inputs=[topic_input, grade_input, provider_input, duration_input, level_input, export_input],
            outputs=[gen_output_md, gen_status, json_file, md_file, docx_file, history_table],
        ).then(
            fn=lambda r: r,
            inputs=[gen_output_md],
            outputs=[gen_output_md],
        )

        # 预设按钮：点击后将指令填入文本框
        for btn, text in preset_btns:
            btn.click(fn=lambda t=text: t, outputs=[import_instructions])
        for btn, text in regen_preset_btns:
            btn.click(fn=lambda t=text: t, outputs=[regen_instructions])

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

        def do_open_folder():
            import subprocess
            folder = get_plans_dir()
            try:
                subprocess.Popen(f'explorer "{folder}"')
                return f"已打开: {folder}"
            except Exception as e:
                return f"打开失败: {e}"

        open_folder_btn.click(fn=do_open_folder, outputs=[history_status])

        def do_save_reflection(current_res, worked, failed, reaction, adjustment):
            if not current_res:
                return "请先点击列表中的教案"
            if not any([worked.strip(), failed.strip(), reaction.strip(), adjustment.strip()]):
                return "请至少填写一项反思内容"
            meta = current_res.get("metadata", {})
            key = get_cache_key(meta.get("topic", ""), meta.get("grade", ""), meta.get("llm_provider", ""))
            if add_reflection(key, worked.strip(), failed.strip(), reaction.strip(), adjustment.strip()):
                return "反思已保存，下次生成同主题教案时会自动参考"
            return "保存失败"

        save_reflection_btn.click(
            fn=do_save_reflection,
            inputs=[current_result, ref_what_worked, ref_what_failed, ref_student_reaction, ref_next_adjustment],
            outputs=[reflection_status],
        )

        # Tab 3: 编辑
        def on_load_for_edit_update_dropdown(plan_d):
            """加载教案时同步更新环节下拉框"""
            if not plan_d:
                return gr.update(choices=[], value=None)
            plan = TeacherRuntimePlan.model_validate(plan_d)
            choices = [f"{i}: {s.title}" for i, s in enumerate(plan.sections)]
            return gr.update(choices=choices, value=choices[0] if choices else None)

        load_for_edit_btn.click(
            fn=load_plan_for_edit,
            inputs=[current_plan_dict],
            outputs=[edit_objectives, edit_sections, edit_homework, edit_interactions, edit_summary],
        ).then(
            fn=lambda plan_d: _plan_to_display_data({"teacher_runtime_plan": plan_d})["md"] if plan_d else "请先加载教案",
            inputs=[current_plan_dict],
            outputs=[edit_preview],
        ).then(
            fn=on_load_for_edit_update_dropdown,
            inputs=[current_plan_dict],
            outputs=[regen_section_idx],
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

        # ── Tab 3: 局部重新生成 ──

        def do_regen_section(plan_d, section_choice, provider, instructions):
            if not plan_d:
                return "请先加载教案", gr.update()
            if not section_choice:
                return "请选择一个环节", gr.update()
            if not instructions.strip():
                return "请输入改进指令", gr.update()

            try:
                section_index = int(section_choice.split(":")[0])
            except (ValueError, IndexError):
                return "环节选择格式错误", gr.update()

            plan = TeacherRuntimePlan.model_validate(plan_d)
            state = {"provider": provider}
            llm_client = get_llm_for_state(state)

            try:
                new_plan = regenerate_section(plan, section_index, instructions.strip(), llm_client)
                md = render_markdown(new_plan)
                quality = score_runtime_plan(new_plan)
                status = f"环节已重新生成 | 评分: {quality['total']}/{quality['max']} ({quality['grade']})"
                return status, md, new_plan.model_dump()
            except Exception as e:
                return f"重新生成失败: {e}", gr.update(), gr.update()

        regen_btn.click(
            fn=do_regen_section,
            inputs=[current_plan_dict, regen_section_idx, regen_provider, regen_instructions],
            outputs=[regen_status, edit_preview, current_plan_dict],
        )

        # ── Tab 4: 导入教案 ──

        def _load_json_from_text_or_file(json_text, uploaded_file):
            """从文本框或上传文件加载 JSON"""
            if uploaded_file is not None:
                try:
                    with open(uploaded_file.name, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    raise ValueError(f"读取文件失败: {e}")

            if not json_text or not json_text.strip():
                raise ValueError("请粘贴教案 JSON 或上传文件")

            try:
                return json.loads(json_text)
            except json.JSONDecodeError as e:
                raise ValueError(f"JSON 解析失败: {e}")

        def do_import_improve(json_text, uploaded_file, topic, grade, provider, instructions):
            if not topic.strip():
                return "请输入教学主题", "", None, gr.update(), gr.update(), gr.update()
            if not grade.strip():
                return "请输入年级", "", None, gr.update(), gr.update(), gr.update()
            if not instructions.strip():
                return "请输入改进指令", "", None, gr.update(), gr.update(), gr.update()

            try:
                raw_data = _load_json_from_text_or_file(json_text, uploaded_file)
            except ValueError as e:
                return str(e), "", None, gr.update(), gr.update(), gr.update()

            # 解析为 TeacherRuntimePlan
            try:
                # 兼容两种格式：直接是 plan dict，或嵌套在 teacher_runtime_plan 中
                if "teacher_runtime_plan" in raw_data:
                    plan_data = raw_data["teacher_runtime_plan"]
                elif "sections" in raw_data:
                    plan_data = raw_data
                else:
                    return "JSON 中找不到教案数据（需要 sections 字段或 teacher_runtime_plan 字段）", "", None, gr.update(), gr.update(), gr.update()

                existing_plan = TeacherRuntimePlan.model_validate(plan_data)
            except Exception as e:
                return f"教案数据解析失败: {e}", "", None, gr.update(), gr.update(), gr.update()

            # 调用 LLM 改进
            state = {"provider": provider}
            llm_client = get_llm_for_state(state)

            try:
                improved = improve_existing_plan(existing_plan, instructions.strip(), topic.strip(), grade.strip(), llm_client)
            except Exception as e:
                return f"改进失败: {e}", "", None, gr.update(), gr.update(), gr.update()

            # 导出
            output_dir = tempfile.mkdtemp(prefix="import_")
            exported = export_outputs(
                {"teacher_runtime_plan": improved.model_dump(), "metadata": {"topic": topic, "grade": grade, "llm_provider": provider}},
                output_dir,
                ["json", "md", "docx"],
                topic,
            )

            display = _plan_to_display_data({"teacher_runtime_plan": improved.model_dump()})
            history_data = _build_history_table()

            return (
                display["status"],
                display["md"],
                improved.model_dump(),
                exported.get("json"),
                exported.get("md"),
                exported.get("docx"),
            )

        import_btn.click(
            fn=do_import_improve,
            inputs=[import_json_input, import_file_input, import_topic, import_grade, import_provider, import_instructions],
            outputs=[import_status, import_preview, current_plan_dict, import_json_file, import_md_file, import_docx_file],
        )

        # ── Tab 5: 单元计划 ──

        def do_unit_plan(topic, grade, total_lessons, provider, duration, level):
            if not topic.strip():
                return "请输入教学主题", "*请输入教学主题*"
            if not grade.strip():
                return "请输入年级", "*请输入年级*"

            from app import run_unit_workflow
            from models.runtime import UnitPlan

            total_lessons = int(total_lessons)
            result = run_unit_workflow(
                topic=topic.strip(),
                grade=grade.strip(),
                total_lessons=total_lessons,
                provider=provider,
                duration=duration,
                level=level,
            )

            if "error" in result:
                return f"生成失败: {result['error']}", "*生成失败*"

            # 渲染单元规划
            unit_data = result.get("unit_plan", {})
            unit = UnitPlan.model_validate(unit_data)

            plan_md = f"## {unit.unit_title}\n\n"
            plan_md += f"**年级**: {unit.grade} | **课时**: {unit.total_lessons} 课时\n\n"
            plan_md += f"**单元目标**: {'；'.join(unit.unit_objectives)}\n\n"
            if unit.key_points:
                plan_md += f"**重点**: {'；'.join(unit.key_points)}\n\n"
            if unit.difficult_points:
                plan_md += f"**难点**: {'；'.join(unit.difficult_points)}\n\n"
            plan_md += f"**递进关系**: {unit.progression_logic}\n\n"
            plan_md += "---\n\n### 各课时大纲\n\n"
            for lo in unit.lessons:
                plan_md += f"**第{lo.lesson_number}课时: {lo.title}**\n"
                plan_md += f"- 核心内容: {lo.core_content}\n"
                plan_md += f"- 目标: {'；'.join(lo.objectives)}\n"
                if lo.prerequisites:
                    plan_md += f"- 前置知识: {lo.prerequisites}\n"
                plan_md += "\n"

            # 渲染各课时教案
            lessons_md = "## 各课时教案\n\n"
            lessons = result.get("lessons", [])
            for i, lesson in enumerate(lessons):
                lesson_num = i + 1
                if "error" in lesson:
                    lessons_md += f"### 第{lesson_num}课时 — 生成失败\n\n"
                    lessons_md += f"错误: {lesson['error']}\n\n---\n\n"
                    continue

                runtime_data = lesson.get("teacher_runtime_plan", {})
                if runtime_data:
                    try:
                        plan = TeacherRuntimePlan.model_validate(runtime_data)
                        lessons_md += f"### 第{lesson_num}课时: {plan.summary[:50] if plan.summary else plan.topic}\n\n"
                        quality = score_runtime_plan(plan)
                        lessons_md += f"*评分: {quality['total']}/{quality['max']} ({quality['grade']})*\n\n"
                        lessons_md += render_markdown(plan)
                        lessons_md += "\n\n---\n\n"
                    except Exception:
                        lessons_md += f"### 第{lesson_num}课时 — 解析失败\n\n---\n\n"

            # 连贯性问题
            issues = result.get("coherence_issues", [])
            if issues:
                lessons_md += "\n## ⚠ 连贯性问题\n\n"
                for issue in issues:
                    lessons_md += f"- {issue}\n"

            status = f"单元计划生成完成 | {len(lessons)} 个课时"
            if issues:
                status += f" | {len(issues)} 个连贯性问题"

            return status, plan_md + "\n\n" + lessons_md

        unit_btn.click(
            fn=do_unit_plan,
            inputs=[unit_topic, unit_grade, unit_lessons_count, unit_provider, unit_duration, unit_level],
            outputs=[unit_status, unit_plan_preview],
        )

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
    )


if __name__ == "__main__":
    main()
