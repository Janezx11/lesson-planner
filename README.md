# AI Teaching Copilot

基于 LangGraph 的智能教案生成系统。输入"教学主题 + 年级"，自动生成完整教案。

## 快速开始

```bash
# 安装依赖
uv sync

# 配置 API Key
cp .env.example .env
# 编辑 .env，填入 MIMO_API_KEY 或 ANTHROPIC_API_KEY

# CLI 运行
uv run python app.py --topic "二次函数" --grade "高二" --provider mimo

# Web UI
uv run python webui.py
```

## 架构

```
输入 (topic + grade)
    │
    ▼
┌─ planner_node ─┐
│  (认知路线)      ├→ design_node → content_node → compiler_node → renderer_node
└─ knowledge_node ┘   (互动)       (内容)        (编译)          (渲染)
   并行执行
    │
    ▼
Teacher Runtime Plan → JSON / Markdown / DOCX
```

6 个 LangGraph 节点，planner 和 knowledge 并行执行，总耗时约 5 分钟。

## LLM 提供商

任何 OpenAI 兼容的提供商只需一行配置：

```python
# llm/config.py 中添加
"deepseek": {"sdk": "openai", "model": "deepseek-chat", "env_key": "DEEPSEEK_API_KEY", ...}
```

内置支持：Mimo、Claude、Qwen、DeepSeek、Groq 等。

## 学科模板

自动识别 10 个学科（数学、物理、化学、生物、语文、英语、历史、地理、信息技术、政治），为每个学科定制：
- 推荐认知阶段和教学策略
- 知识结构分析重点
- 练习题设计指导
- 教学目标常用动词

## 缓存

相同主题 + 年级 + 提供商的组合自动缓存，重复生成秒出结果。

```bash
uv run python app.py --clear-cache    # 清除缓存
uv run python app.py --no-cache       # 跳过缓存
```

## Web UI

```bash
uv run python webui.py
```

三个 Tab：
- **生成教案** — 输入主题，生成并预览
- **历史教案** — 浏览、搜索、删除历史教案
- **编辑教案** — 在线修改教学目标、环节、作业

## 测试

```bash
uv run python -m pytest tests/ -v
```

90 个单元测试，覆盖 JSON 修复、配置系统、工厂路由、编译器质量、学科模板、缓存。

## 项目结构

```
lesson-planner/
├── app.py                  # CLI 入口
├── webui.py                # Gradio Web UI
├── cache.py                # 文件缓存
├── graph/
│   ├── state.py            # TeachingState (Pydantic BaseModel)
│   └── builder.py          # LangGraph 工作流构建器
├── nodes/
│   ├── planner_node.py     # 认知路线设计
│   ├── knowledge_node.py   # 知识结构分析
│   ├── design_node.py      # 互动设计
│   ├── content_node.py     # 教学内容生成
│   ├── compiler_node.py    # 认知 IR → 教师教案
│   └── renderer_node.py    # 渲染输出
├── models/
│   ├── cognitive/          # Cognitive IR 模型（AI 内部）
│   ├── runtime/            # Teacher Runtime Plan（教师可读）
│   └── subjects.py         # 学科模板
├── llm/
│   ├── base.py             # LLM 抽象层 + 工厂
│   ├── config.py           # 配置管理
│   ├── openai_client.py    # 通用 OpenAI 兼容客户端
│   ├── claude.py           # Anthropic 客户端
│   └── json_repair.py      # 统一 JSON 修复
├── compiler/
│   ├── pedagogical_compiler.py  # 认知术语清洗 + 质量评分
│   └── prompt_builder.py        # 编译器 Prompt 构建
├── exporters/              # JSON / Markdown / DOCX 导出
├── renderers/              # Markdown 渲染
├── prompts/                # 各节点 Prompt 模板
└── tests/                  # 90 个单元测试
```

## 输出质量

- 认知术语自动清洗（16 条替换规则）
- 5 维质量评分系统（字段完整性、术语清洁度、时间合理性、互动设计、练习与作业）
- 输出强类型 Pydantic Model，不输出自由文本

## 许可证

MIT License
