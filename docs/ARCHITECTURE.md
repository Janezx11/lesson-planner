# 系统架构设计

## 🎯 设计理念

AI Teaching Copilot 采用模块化、可扩展的架构设计，基于 LangGraph 构建多阶段工作流。整个系统强调：

- **单一职责原则**: 每个节点只负责一个明确的功能
- **数据不可变性**: State 在节点间传递，确保可追溯性
- **错误隔离**: 每个节点都有独立的错误处理机制
- **可维护性**: 清晰的代码结构和文档

## 🏗️ 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Teaching Copilot                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   CLI/App   │  │    API      │  │ Integration │        │
│  │ Interface   │  │  Endpoint   │  │   Points    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph Workflows                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Planner     │  │ Knowledge   │  │  Design     │        │
│  │ Node        │  │ Node        │  │  Node       │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Content     │  │ Formatter   │  │    END      │        │
│  │ Node        │  │ Node        │  │             │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                     Data Flow & Storage                     │
├─────────────────────────────────────────────────────────────┤
│  JSON ↔ Memory ↔ File System ↔ External APIs              │
└─────────────────────────────────────────────────────────────┘
```

## 📦 模块详解

### 1. Core Components（核心组件）

#### `graph/state.py`
**职责**: 定义系统的核心数据结构和类型

```python
class TeachingState(TypedDict):
    topic: str           # 输入的教学主题
    grade: str          # 年级信息
    plan: dict          # 教学计划
    knowledge: dict    # 知识结构
    design: dict       # 教学设计
    content: dict      # 教学内容
    final_output: dict # 最终输出
    error_count: int    # 错误计数
    max_retries: int    # 最大重试次数
```

**设计特点**:
- 使用 Pydantic 模型进行类型验证
- TypedDict 确保类型安全
- 每个字段有明确的职责划分

#### `graph/builder.py`
**职责**: 构建和管理 LangGraph 工作流

```python
class WorkflowBuilder:
    def build_workflow(self) -> CompiledGraph:
        # 注册所有节点
        # 配置工作流边
        # 编译并返回工作流图
```

**设计特点**:
- 工厂模式创建节点函数
- 线性工作流设计（可扩展为条件工作流）
- 预编译优化性能

### 2. Nodes（节点层）

#### `nodes/planner_node.py`
**职责**: 制定教学计划

**输入**: topic, grade, plan (空)
**输出**: plan (包含教学目标、知识点等)

**执行流程**:
1. 读取 planner.txt Prompt
2. 调用 Claude API 生成结构化输出
3. 验证 JSON Schema
4. 更新 State 中的 plan 字段
5. 错误处理和重试机制

#### `nodes/knowledge_node.py`
**职责**: 分析知识结构

**输入**: topic, grade, plan, knowledge (空)
**输出**: knowledge (包含核心概念、易错点等)

**执行流程**:
1. 基于 plan 分析知识层次
2. 识别学习难点和关键洞察
3. 生成概念层级结构

#### `nodes/design_node.py`
**职责**: 设计教学流程

**输入**: topic, grade, plan, knowledge, design (空)
**输出**: design (包含教学阶段、互动设计等)

**执行流程**:
1. 整合 plan 和 knowledge 信息
2. 设计分阶段教学流程
3. 制定差异化策略

#### `nodes/content_node.py`
**职责**: 生成具体教学内容

**输入**: topic, grade, design, content (空)
**输出**: content (包含例题、练习题、互动元素等)

**执行流程**:
1. 根据设计生成具体的教学内容
2. 提供多样化的练习题目
3. 设计课堂互动环节

#### `nodes/formatter_node.py`
**职责**: 格式化最终输出

**输入**: topic, grade, plan, knowledge, design, content
**输出**: final_output (整合所有信息的完整方案)

**执行流程**:
1. 聚合所有节点的输出
2. 生成执行摘要和实施指南
3. 添加元数据和评估框架

### 3. LLM Layer（大语言模型层）

#### `llm/claude.py`
**职责**: Claude API 的统一封装

```python
class ClaudeClient:
    def generate_structured_output(self, prompt, schema, system_prompt)
    def generate_text(self, prompt, system_prompt)
    def _ensure_json_format(self, text)  # 自动修复 JSON
```

**设计特点**:
- 统一的错误处理
- 自动 JSON 解析和修复
- 支持结构化输出
- 全局单例模式

### 4. Utilities（工具层）

#### `utils/parser.py`
**职责**: 提供通用的解析和验证工具

```python
def safe_parse_json(text, fallback_key="raw_response")
def validate_required_fields(data, required_fields)
def merge_dicts_safe(dict1, dict2)
def extract_json_from_markdown(markdown_text)
```

**设计特点**:
- 防御性编程
- 多种修复策略
- 安全的字典合并

## 🔄 数据流设计

### State 流转图

```
Initial State
    │
    ▼
[topic, grade] → planner_node
    │
    ▼
[topic, grade, plan] → knowledge_node
    │
    ▼
[topic, grade, plan, knowledge] → design_node
    │
    ▼
[topic, grade, plan, knowledge, design] → content_node
    │
    ▼
[topic, grade, plan, knowledge, design, content] → formatter_node
    │
    ▼
[final_output] ← END
```

### 错误传播机制

```
Node Error Handling Flow:
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Node A    │     │   Node B    │     │   Node C    │
│  Failure    │────▶│  Retry      │────▶│  Fallback   │
│             │     │             │     │             │
│ Default     │◀────│ Default     │◀────│  Success    │
│ Values      │     │ Values      │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
```

## 🚀 扩展性设计

### 1. 新增节点类型

**步骤**:
1. 在 `nodes/` 下创建新节点文件
2. 实现节点函数 (符合 State 接口)
3. 在 `graph/builder.py` 中注册节点
4. 更新 `graph/state.py` 中的 State 定义

**示例**:
```python
# nodes/new_node.py
def new_node(state: TeachingState) -> TeachingState:
    # 实现逻辑
    return state

# graph/builder.py
workflow.add_node("new_node", new_node)
```

### 2. 条件工作流

当前是线性工作流，未来可以扩展为：

```python
workflow.add_conditional_edges(
    "planner_node",
    lambda state: "knowledge_node" if state["plan"] else "error_node"
)
```

### 3. RAG 集成预留

预留了以下接口用于未来 RAG 集成：

```python
# 在 State 中预留字段
rag_context: List[str]
vector_db_results: List[Dict]

# 在节点中预留调用
def query_knowledge_base(query: str) -> List[str]:
    # 未来实现
    pass
```

### 4. Tool 调用接口

预留工具调用接口：

```python
class ToolRegistry:
    @staticmethod
    def register_tool(name: str, func: Callable):
        # 注册工具函数
        pass

# 示例工具
@ToolRegistry.register_tool
def calculate_difficulty(level: str) -> float:
    # 计算难度系数
    pass
```

## 🛡️ 错误处理策略

### 分层错误处理

1. **LLM Layer**: API 错误、超时、网络问题
2. **Parser Layer**: JSON 解析失败、格式错误
3. **Node Layer**: 业务逻辑错误、验证失败
4. **Workflow Layer**: 状态传递错误、工作流中断

### 重试机制

```python
max_retries = 3
for attempt in range(max_retries):
    try:
        # 执行操作
        break
    except Exception as e:
        if attempt == max_retries - 1:
            # 最后一次尝试失败
            raise
        time.sleep(1)  # 指数退避
```

### 降级策略

1. **JSON 解析失败**: 使用原始文本作为 fallback
2. **API 调用失败**: 返回默认值或简化版本
3. **节点执行失败**: 跳过该节点继续后续处理

## 📊 监控和日志

### 日志级别

- **DEBUG**: 详细的调试信息，包括 API 请求
- **INFO**: 重要的运行信息，节点开始/结束
- **WARNING**: 潜在的问题，如重试、降级
- **ERROR**: 错误信息，包括异常堆栈
- **CRITICAL**: 严重错误，工作流终止

### 性能指标

- **响应时间**: 单个节点的平均处理时间
- **成功率**: 节点执行的 success rate
- **重试率**: 需要重试的操作比例
- **API 调用**: 每个工作流的 API 调用次数

## 🧪 测试策略

### 单元测试
- 每个节点独立测试
- State 对象的正确性验证
- JSON Schema 验证

### 集成测试
- 完整工作流执行测试
- 错误场景测试
- 性能测试

### Mock 策略
- 模拟 Claude API 响应
- Mock 文件 I/O 操作
- 模拟网络延迟和错误

## 🔒 安全和隐私

### 数据保护
- API Key 存储在环境变量中
- 敏感信息不记录到日志
- 临时文件的及时清理

### 输入验证
- Prompt 模板的内容验证
- JSON Schema 验证
- 必需字段的检查

## 📈 部署考虑

### 容器化
```dockerfile
FROM python:3.9-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . /app
WORKDIR /app
CMD ["python", "app.py"]
```

### 配置管理
- 环境变量配置
- 配置文件支持
- 运行时参数调整

这个架构设计确保了系统的可维护性、可扩展性和可靠性，为未来的功能扩展奠定了坚实的基础。