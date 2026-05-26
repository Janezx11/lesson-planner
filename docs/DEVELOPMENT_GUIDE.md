# 开发指南

## 开发环境

```bash
git clone https://github.com/Janezx11/lesson-planner.git
cd lesson-planner
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## 项目结构

```
lesson-planner/
├── app.py                    # CLI 入口
├── graph/                    # LangGraph 工作流
│   ├── state.py              # TeachingState 定义
│   └── builder.py            # 工作流构建器
├── models/
│   ├── cognitive/            # Cognitive IR (AI 内部)
│   ├── runtime/              # Teacher Runtime (教师可读)
│   └── content.py            # content_node 输出模型
├── compiler/                 # LLM 编译器
│   ├── pedagogical_compiler.py
│   └── prompt_builder.py
├── nodes/                    # LangGraph 节点
├── renderers/                # 格式渲染
├── exporters/                # 文档导出
├── llm/                      # LLM 抽象层
├── prompts/                  # Prompt 模板
├── tests/
└── outputs/                  # 导出文件 (gitignore)
```

## 添加新节点

1. 创建节点文件 `nodes/new_node.py`
2. 实现节点函数，返回 partial update
3. 在 `nodes/__init__.py` 中导出
4. 在 `graph/builder.py` 中注册

```python
# nodes/new_node.py
from graph.state import TeachingState
from llm.factory import get_llm_for_state

def new_node(state: TeachingState) -> dict:
    llm_client = get_llm_for_state(state.model_dump())
    output = llm_client.generate_structured_output_v2(
        prompt=prompt,
        output_model=SomePydanticModel,
        system_prompt="..."
    )
    return {"field": output.model_dump()}

def create_new_node():
    return new_node
```

## 添加新导出器

1. 创建 `exporters/new_exporter.py`
2. 实现纯函数，不调用 LLM
3. 在 `exporters/__init__.py` 中导出
4. 在 `app.py` 的 `export_outputs` 中集成

```python
# exporters/new_exporter.py
from models.runtime import TeacherRuntimePlan

def export_to_new(plan: TeacherRuntimePlan, path: str) -> str:
    # 纯格式转换
    ...
    return path
```

## LLM 调用模式

所有节点使用统一的 v2 接口：

```python
from llm.factory import get_llm_for_state

llm_client = get_llm_for_state(state.model_dump())
result = llm_client.generate_structured_output_v2(
    prompt=prompt,
    output_model=PydanticModel,  # 自动生成 JSON Schema
    system_prompt=system_prompt
)
# result 是强类型 Pydantic 实例
return {"field": result.model_dump()}
```

## 错误处理模式

```python
max_retries = 3
for attempt in range(max_retries):
    try:
        output = llm_client.generate_structured_output_v2(...)
        issues = validate_business_rules(output)
        if not issues:
            return {"field": output.model_dump()}
        if attempt == max_retries - 1:
            return {"field": output.model_dump()}
    except ValidationError:
        if attempt == max_retries - 1:
            return {"field": default_output.model_dump()}
```

## CLI 用法

```bash
# 基本用法（只输出 JSON）
python app.py --topic "二次函数" --grade "高中二年级"

# 导出 DOCX
python app.py --topic "英语的现在进行时" --grade "初中一年级" --export docx

# 导出所有格式
python app.py --topic "网络分层" --grade "职高" --export all

# 指定 LLM 和输出目录
python app.py --topic "光合作用" --grade "高一" --provider qwen --output-dir my_outputs
```

## 测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行单个测试
python -m pytest tests/test_models.py -v
```
