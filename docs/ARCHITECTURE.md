# 系统架构设计

## 设计理念

AI Teaching Copilot 采用"教学认知编译系统"架构，将 AI 内部认知结构编译为教师可读的教案文档。

核心原则：
- **认知与呈现分离**: Cognitive IR (AI 内部) ≠ Teacher Runtime (教师可读)
- **编译而非渲染**: 使用 LLM 进行语义转换，而非简单的模板填充
- **强类型输出**: 所有 LLM 输出使用 Pydantic Model，自动校验
- **错误隔离**: 每个节点都有独立的重试和降级机制

## 五层架构

```
Layer 1: Cognitive IR (AI 内部认知)
  models/cognitive/ — 认知阶段、知识结构、互动策略

Layer 2: Compiler (LLM 语义转换)
  compiler/ — 将认知术语转为教师语言

Layer 3: Teacher Runtime Model (教师可读教案)
  models/runtime/ — 课堂环节、师生互动、练习作业

Layer 4: Renderer (格式化)
  renderers/ — Runtime Model → Markdown

Layer 5: Exporter (文档导出)
  exporters/ — Runtime Model → DOCX / MD 文件
```

## LangGraph 工作流

```
planner_node (CognitiveFlow)
    ↓
knowledge_node (KnowledgeStructure)
    ↓
design_node (InteractionDesign)
    ↓
content_node (ContentOutput)
    ↓
compiler_node (TeacherRuntimePlan)  ← LLM 语义转换
    ↓
renderer_node (Markdown + final_output)
    ↓
END
```

## 状态定义

```python
class TeachingState(BaseModel):
    # 输入
    topic: str
    grade: str
    provider: str = "claude"

    # Cognitive IR (由前 4 个节点填充)
    plan: Dict[str, Any]          # CognitiveFlow
    knowledge: Dict[str, Any]     # KnowledgeStructure
    design: Dict[str, Any]        # InteractionDesign
    content: Dict[str, Any]       # ContentOutput

    # Runtime (由 compiler_node 填充)
    runtime: Dict[str, Any]       # TeacherRuntimePlan

    # 输出 (由 renderer_node 填充)
    final_output: Dict[str, Any]  # metadata + markdown + statistics

    # 控制
    error_count: int = 0
    max_retries: int = 3
```

## 节点职责

| 节点 | 输入 | 输出 | 是否调用 LLM |
|------|------|------|-------------|
| planner_node | topic, grade | CognitiveFlow | Yes |
| knowledge_node | plan | KnowledgeStructure | Yes |
| design_node | plan | InteractionDesign | Yes |
| content_node | plan, design | ContentOutput | Yes |
| compiler_node | 全部 Cognitive IR | TeacherRuntimePlan | Yes |
| renderer_node | runtime | Markdown + final_output | No |

## LLM 层

```python
# 统一接口
llm_client = get_llm_for_state(state)
result = llm_client.generate_structured_output_v2(
    prompt=prompt,
    output_model=SomePydanticModel,  # 自动从 Model 生成 JSON Schema
    system_prompt=system_prompt
)
# result 是强类型 Pydantic Model 实例
```

支持的提供商：Claude、Qwen、LongCat

## 错误处理

每个节点遵循相同的重试模式：

```python
max_retries = 3
for attempt in range(max_retries):
    try:
        output = llm_client.generate_structured_output_v2(...)
        issues = validate_business_rules(output)
        if not issues:
            return {"field": output.model_dump()}
        if attempt == max_retries - 1:
            return {"field": output.model_dump()}  # 使用当前结果
    except ValidationError:
        if attempt == max_retries - 1:
            return {"field": default_output.model_dump()}  # 降级
```

## 项目结构

```
lesson-planner/
├── app.py                    # CLI 入口
├── graph/
│   ├── state.py              # TeachingState 定义
│   └── builder.py            # LangGraph 工作流构建
├── models/
│   ├── cognitive/            # Cognitive IR 模型
│   ├── runtime/              # Teacher Runtime 模型
│   └── content.py            # content_node 输出模型
├── compiler/
│   ├── pedagogical_compiler.py  # 核心编译器
│   └── prompt_builder.py        # Prompt 构建
├── nodes/
│   ├── planner_node.py
│   ├── knowledge_node.py
│   ├── design_node.py
│   ├── content_node.py
│   ├── compiler_node.py
│   └── renderer_node.py
├── renderers/
│   └── markdown_renderer.py
├── exporters/
│   ├── docx_exporter.py
│   └── markdown_exporter.py
├── llm/
│   ├── base.py               # 抽象接口
│   ├── config.py             # 配置管理
│   ├── factory.py            # 工厂模式
│   ├── claude.py
│   ├── qwen.py
│   └── longcat.py
├── prompts/                  # Prompt 模板
├── tests/
└── outputs/                  # 导出文件（gitignore）
```
