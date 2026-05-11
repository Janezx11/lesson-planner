# AI Teaching Copilot - 教学认知Agent

> 从"教案生成器"到"教学认知Agent"的架构升级

一个基于 LangGraph 的 AI 教学系统，采用**认知驱动**的教学设计理念，而非传统的"情境导入→新课讲解→课堂练习→总结提升"模式。

## 核心理念

### 传统教案生成器 vs 教学认知Agent

| 项目 | 传统教案生成器 | 教学认知Agent |
|------|--------------|--------------|
| **设计理念** | 教师流程驱动 | 学生认知推进驱动 |
| **阶段设计** | 固定四阶段 | 动态认知阶段 |
| **stage_name** | 情境导入、新课讲解... | 认知冲突：为什么网络通信不能乱来 |
| **teacher_activity** | 讲解XXX、引导理解 | 播放动画、展示案例、组织活动 |
| **学科绑定** | 绑定具体学科 | 通用教学行为层（学科无关） |

### 认知阶段类型

系统根据主题动态生成认知阶段：

- **认知冲突**：制造学生的认知矛盾，激发思考
- **猜想建立**：让学生基于已有知识进行推测
- **错误辨析**：通过典型错误引发反思
- **规律发现**：引导学生从现象中归纳规律
- **模型建构**：帮助学生建立抽象模型
- **迁移应用**：将所学应用到新情境
- **实践验证**：通过动手验证理论
- **案例分析**：通过案例深化理解

## 架构设计

### 多节点协作工作流

```
planner_node (认知路线设计)
    ↓
knowledge_node (知识结构分析)
    ↓
design_node (通用教学行为) ← 学科无关
    ↓
content_node (学科内容填充) ← 具体知识
    ↓
formatter_node (最终整合)
```

### 节点职责

| 节点 | 职责 | 输入 | 输出 |
|------|------|------|------|
| **planner_node** | 设计认知推进路线 | 主题、年级 | 认知阶段、认知递进路径 |
| **knowledge_node** | 分析知识结构 | 主题、年级 | 核心概念、易错点、前置知识 |
| **design_node** | 设计通用教学行为 | 认知路线 | 互动模式、提问策略、反馈机制 |
| **content_node** | 生成学科内容 | 认知路线 + 教学行为 | 练习题、板书、作业、教师话术 |
| **formatter_node** | 整合最终输出 | 所有节点输出 | 完整教学方案 |

### 状态管理（LangGraph 标准模式）

项目采用标准 LangGraph 状态管理模式：

#### Pydantic BaseModel 状态定义

```python
class TeachingState(BaseModel):
    # 输入字段
    topic: str = Field(description="教学主题")
    grade: str = Field(description="年级信息")

    # 配置字段
    provider: str = Field(default="claude", description="LLM 提供商")

    # 节点输出字段（由各节点填充）
    plan: Dict[str, Any] = Field(default_factory=dict)
    knowledge: Dict[str, Any] = Field(default_factory=dict)
    design: Dict[str, Any] = Field(default_factory=dict)
    content: Dict[str, Any] = Field(default_factory=dict)
    final_output: Dict[str, Any] = Field(default_factory=dict)

    # 控制字段
    error_count: int = Field(default=0)
    max_retries: int = Field(default=3)
```

#### Partial Update 模式

所有节点返回 partial update（只返回修改的字段），由 LangGraph 自动合并：

```python
# 节点返回格式
def planner_node(state: TeachingState) -> Dict[str, Any]:
    # ... 业务逻辑 ...
    return {"plan": plan_data}  # 只返回 plan 字段

def design_node(state: TeachingState) -> Dict[str, Any]:
    # ... 业务逻辑 ...
    return {"design": design_data}  # 只返回 design 字段
```

#### 错误处理标准化

```python
def _handle_error(state: TeachingState, error_msg: str) -> Dict[str, Any]:
    return {
        "plan": default_plan,
        "error_count": state.error_count + 1  # 递增错误计数
    }
```

### Pydantic 强类型模型

所有节点输出都使用 Pydantic Model 定义，自动保证类型安全：

```python
# models/planner.py
class TeachingStage(BaseModel):
    stage_name: str = Field(description="阶段名称")
    teaching_strategy: str = Field(description="教学策略")
    teacher_activity: List[str] = Field(default_factory=list)
    student_activity: List[str] = Field(default_factory=list)

class PlannerOutput(BaseModel):
    lesson_overview: str = Field(description="认知主线")
    cognitive_progression: List[str] = Field(default_factory=list)
    teaching_process: List[TeachingStage] = Field(default_factory=list)
```

```python
# models/design.py
class TeacherBehavior(BaseModel):
    action: str = Field(description="具体行动")
    purpose: str = Field(description="行动目的")

class InteractionDesign(BaseModel):
    stage_name: str = Field(description="阶段名称")
    interaction_type: str = Field(description="互动类型")
    teacher_behavior: TeacherBehavior = Field(description="教师行为")
    student_behavior: StudentBehavior = Field(description="学生行为")
```

### 核心字段

#### planner_node 输出 (PlannerOutput)

```json
{
  "lesson_overview": "认知主线描述",
  "cognitive_progression": [
    "学生初始状态：...",
    "阶段1后：...",
    "最终状态：..."
  ],
  "teaching_process": [
    {
      "stage_name": "认知冲突：为什么网络通信不能乱来",
      "cognitive_state": "学生当前认知状态",
      "cognitive_goal": "本阶段认知目标",
      "teaching_strategy": "认知冲突",
      "teacher_activity": ["播放混乱动画", "展示抓包截图"],
      "student_activity": ["观察动画", "尝试回答"],
      "expected_cognitive_change": "从认为简单到意识到需要规则"
    }
  ]
}
```

#### design_node 输出 (DesignOutput)

```json
{
  "interaction_design": [
    {
      "stage_name": "认知冲突阶段",
      "interaction_type": "问题驱动",
      "pedagogy_method": "启发式教学",
      "teacher_behavior": {
        "action": "提出开放性问题，等待学生思考",
        "purpose": "激发认知冲突"
      },
      "student_behavior": {
        "action": "独立思考，尝试回答",
        "cognitive_activity": "分析问题，调用已有知识"
      },
      "cognitive_level": "分析"
    }
  ],
  "question_strategy": {
    "approach": "递进式提问",
    "progression": "从具体到抽象"
  }
}
```

## 技术栈

- **Python 3.9+**
- **LangGraph**：工作流编排
- **Pydantic**：状态模型和类型验证
- **多LLM提供商**：LongCat、Claude、Qwen
- **OpenAI兼容SDK**：统一API接口

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，设置 API Key
LONGCAT_API_KEY=your_key_here
# 或
ANTHROPIC_API_KEY=your_key_here
# 或
QWEN_API_KEY=your_key_here
```

### 3. 运行

```bash
# 使用 LongCat
python app.py --topic "二次函数" --grade "高中二年级" --provider longcat

# 使用 Claude
python app.py --topic "网络分层" --grade "职高" --provider claude

# 使用 Qwen
python app.py --topic "光合作用" --grade "高中一年级" --provider qwen
```

## 项目结构

```
lesson-planner/
├── app.py                    # 主应用入口
├── graph/
│   ├── __init__.py           # 模块导出
│   ├── state.py              # Pydantic BaseModel 状态定义
│   └── builder.py            # LangGraph 工作流构建器
├── models/                   # Pydantic 强类型模型（新增）
│   ├── __init__.py           # 模块导出
│   ├── planner.py            # planner_node 输出模型
│   ├── knowledge.py          # knowledge_node 输出模型
│   ├── design.py             # design_node 输出模型
│   ├── content.py            # content_node 输出模型
│   └── final.py              # formatter_node 输出模型
├── nodes/
│   ├── __init__.py           # 模块导出
│   ├── planner_node.py       # 认知路线设计节点
│   ├── knowledge_node.py     # 知识结构分析节点
│   ├── design_node.py        # 通用教学行为节点（学科无关）
│   ├── content_node.py       # 学科内容生成节点
│   └── formatter_node.py     # 最终整合节点
├── llm/
│   ├── __init__.py           # 模块导出
│   ├── base.py               # LLM 基础抽象层（支持 Pydantic Model）
│   ├── config.py             # 配置管理（严格隔离业务字段）
│   ├── factory.py            # 工厂模式（状态→配置→客户端）
│   ├── longcat.py            # LongCat API 客户端
│   ├── claude.py             # Claude API 客户端
│   └── qwen.py               # Qwen API 客户端
├── prompts/
│   ├── planner.txt           # 认知路线设计 prompt
│   ├── knowledge.txt         # 知识结构分析 prompt
│   ├── interaction.txt       # 通用教学行为 prompt（学科无关）
│   ├── content.txt           # 学科内容生成 prompt
│   └── formatter.txt         # 最终整合 prompt
├── utils/
│   ├── __init__.py           # 模块导出
│   ├── logger.py             # 日志工具
│   └── parser.py             # JSON 解析工具
├── tests/
│   └── __init__.py           # 测试模块
└── docs/
    ├── ARCHITECTURE.md       # 架构文档
    ├── DEVELOPMENT_GUIDE.md  # 开发指南
    └── PROJECT_OVERVIEW.md   # 项目概览
```

## LLM 配置系统

### 严格分层设计

```
State (业务字段: topic, grade, ...)
    ↓
get_llm_for_state(state)
    ↓
LLMConfig.from_state(provider, state)  ← 只提取模型参数
    ↓
LLMClientFactory.create(provider, config)
    ↓
Client (LongCatClient / ClaudeClient / QwenClient)
```

### 配置字段

```python
@dataclass
class LLMConfig:
    provider: str          # 提供商
    model: str             # 模型名称
    temperature: float     # 温度
    max_tokens: int        # 最大token数
    base_url: str          # API地址
    api_key: str           # API密钥
    timeout: int           # 超时时间
```

**重要**：业务字段（topic、grade等）永远不会进入 LLMConfig。

## 设计原则

### 1. 认知驱动

- 不使用固定的"四阶段"模式
- 根据主题动态生成认知阶段
- 关注学生认知状态变化

### 2. 学科无关的教学行为

- design_node 只设计"怎么教"，不设计"教什么"
- 通用教学行为可复用于不同学科
- content_node 负责填充具体学科内容

### 3. 严格分层

- 配置与业务逻辑隔离
- 每个节点职责单一
- 输出格式统一且可验证

### 4. LangGraph 标准状态管理

- 使用 Pydantic BaseModel 定义状态
- 所有节点返回 partial update
- 由 workflow 层负责 state merge
- 支持类型验证和自动序列化

### 5. Pydantic 强类型结构化输出

- 所有节点输出使用 Pydantic Model
- 删除手写 JSON Schema dict
- 使用 `generate_structured_output_v2()` 自动校验
- 自动从 Pydantic Model 生成 JSON Schema
- ValidationError 自动捕获和处理

```python
# 节点内部使用强类型 Model
from models.planner import PlannerOutput, TeachingStage

# 自动从 Pydantic Model 生成 schema
planner_output = llm_client.generate_structured_output_v2(
    prompt=prompt,
    output_model=PlannerOutput,  # Pydantic Model 类
    system_prompt=system_prompt
)

# 返回类型安全的 partial update
return {"plan": planner_output.model_dump()}
```

### 6. 多提供商支持

- 统一的 LLM 抽象层
- 支持 LongCat、Claude、Qwen
- 易于扩展新的提供商

## 示例输出

```json
{
  "metadata": {
    "topic": "网络分层",
    "grade": "职高",
    "generated_at": "2026-05-08T16:00:00Z"
  },
  "lesson_overview": "通过认知冲突→规律发现→模型建构的路径，帮助学生理解网络分层的必要性",
  "cognitive_progression": [
    "学生初始状态：认为通信就是直接发送",
    "阶段1后：意识到通信会冲突",
    "阶段2后：理解需要规则",
    "最终状态：建立分层模型的整体认知"
  ],
  "teaching_process": [...],
  "interaction_design": [...],
  "practice_design": {...},
  "blackboard_design": {...},
  "homework": [...]
}
```

## 开发指南

### 添加新的 LLM 提供商

1. 在 `llm/` 目录下创建新的客户端文件
2. 继承 `BaseLLMClient` 类
3. 实现 `generate_structured_output` 和 `generate_text` 方法
4. 在 `llm/factory.py` 中注册

### 添加新的认知阶段类型

1. 在 `nodes/planner_node.py` 中更新 `COGNITIVE_STAGE_TYPES` 列表
2. 更新 prompt 中的认知阶段说明
3. 更新验证逻辑

### 自定义教学行为

1. 在 `nodes/design_node.py` 中更新 `INTERACTION_TYPES` 列表
2. 更新 `PEDAGOGY_METHODS` 列表
3. 更新 prompt 中的教学行为说明

### 添加新节点

1. 在 `nodes/` 目录下创建新节点文件
2. 实现节点函数，返回 partial update
3. 在 `nodes/__init__.py` 中导出
4. 在 `graph/builder.py` 中注册节点和边

```python
# 新节点示例
def new_node(state: TeachingState) -> Dict[str, Any]:
    # 读取状态
    topic = state.topic
    # ... 业务逻辑 ...

    # 返回 partial update（只返回修改的字段）
    return {"new_field": new_data}
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

- GitHub: [Janezx11](https://github.com/Janezx11)
- 项目地址: [lesson-planner](https://github.com/Janezx11/lesson-planner)
