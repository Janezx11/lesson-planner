# 开发指南

## 🛠️ 开发环境设置

### 1. 克隆项目
```bash
git clone https://github.com/your-username/ai-teaching-copilot.git
cd ai-teaching-copilot
```

### 2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 配置开发工具
```bash
# 安装开发依赖（可选）
pip install pytest black flake8 mypy

# 配置 pre-commit hook（可选）
pre-commit install
```

## 🏗️ 项目结构详解

```
ai-teaching-copilot/
├── app.py                    # 主应用入口
├── graph/
│   ├── state.py             # State 定义和类型系统
│   └── builder.py           # LangGraph 工作流构建器
├── nodes/                   # 节点实现目录
│   ├── __init__.py          # 包初始化文件
│   ├── planner_node.py      # 规划节点
│   ├── knowledge_node.py    # 知识节点
│   ├── design_node.py       # 设计节点
│   ├── content_node.py      # 内容节点
│   └── formatter_node.py    # 格式化节点
├── llm/                     # LLM 封装层
│   ├── __init__.py          # 包初始化文件
│   └── claude.py            # Claude API 封装
├── prompts/                 # Prompt 模板目录
│   ├── planner.txt         # 规划节点模板
│   ├── knowledge.txt       # 知识节点模板
│   ├── design.txt          # 设计节点模板
│   ├── content.txt         # 内容节点模板
│   └── formatter.txt       # 格式化节点模板
├── utils/                   # 工具函数目录
│   ├── __init__.py          # 包初始化文件
│   └── parser.py            # 解析和验证工具
├── tests/                   # 测试目录
│   ├── __init__.py          # 包初始化文件
│   └── test_basic.py        # 基础测试
├── docs/                    # 文档目录
│   ├── ARCHITECTURE.md      # 架构说明
│   ├── DEVELOPMENT_GUIDE.md # 本文件
│   └── CONTRIBUTING.md      # 贡献指南
├── examples/                # 示例文件
│   └── sample_output.json   # 示例输出
├── .env.example             # 环境变量示例
├── requirements.txt         # Python 依赖
├── pyproject.toml           # 项目配置
├── README.md               # 项目说明
└── QUICKSTART.md          # 快速开始指南
```

## 📝 代码风格和规范

### Python 编码规范

#### 1. 命名约定
```python
# 变量和函数: snake_case
user_name = "John"
def calculate_score(data):
    pass

# 类名: PascalCase
class TeachingNode:
    pass

# 常量: UPPER_SNAKE_CASE
MAX_RETRIES = 3
DEFAULT_TEMPERATURE = 0.7
```

#### 2. 类型注解
```python
from typing import Dict, List, Optional, TypedDict

def process_data(data: Dict[str, Any]) -> List[str]:
    """处理数据并返回字符串列表"""
    return [str(item) for item in data.values()]

class UserProfile(TypedDict):
    name: str
    age: int
    preferences: List[str]
```

#### 3. Docstring 格式
```python
def generate_lesson(topic: str, grade: str) -> Dict[str, Any]:
    """
    生成教学方案的主函数。

    Args:
        topic: 教学主题
        grade: 年级信息

    Returns:
        包含完整教学方案的字典

    Raises:
        ValueError: 当输入参数无效时
        RuntimeError: 当工作流执行失败时

    Example:
        >>> result = generate_lesson("二次函数", "高中二年级")
        >>> "metadata" in result
        True
    """
```

### 日志规范

```python
import logging

logger = logging.getLogger(__name__)

def some_function():
    logger.debug("详细的调试信息")
    logger.info("重要的运行信息")
    logger.warning("潜在的问题")
    logger.error("错误信息")
    logger.critical("严重错误")
```

## 🔧 核心模块开发

### 1. 添加新节点

**步骤 1**: 创建节点文件
```bash
# 在 nodes/ 目录下创建新文件
touch nodes/new_node.py
```

**步骤 2**: 实现节点函数
```python
# nodes/new_node.py
from typing import Dict, Any
from langgraph.graph import StateGraph
from graph.state import TeachingState
from llm.claude import get_claude_client

def new_node(state: TeachingState) -> TeachingState:
    """
    新节点的功能描述。

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    topic = state["topic"]
    grade = state["grade"]

    try:
        # 读取 Prompt 模板
        with open("prompts/new_node.txt", "r", encoding="utf-8") as f:
            prompt_template = f.read()

        # 构建 Prompt
        prompt = prompt_template.format(topic=topic, grade=grade)

        # 调用 Claude API
        client = get_claude_client()
        new_data = client.generate_structured_output(
            prompt=prompt,
            schema={"new_field": str},  # 定义期望的 Schema
            system_prompt="你是一个专业的教学专家。"
        )

        # 更新状态
        state["new_field"] = new_data["new_field"]
        return state

    except Exception as e:
        logger.error(f"new_node 执行失败: {e}")
        state["new_field"] = {"error": str(e)}
        return state

def create_new_node():
    """创建新节点函数"""
    return new_node
```

**步骤 3**: 注册节点
```python
# graph/builder.py
from nodes.new_node import create_new_node

class WorkflowBuilder:
    def _register_nodes(self, workflow: StateGraph):
        # ... 现有代码 ...
        new_func = create_new_node()
        workflow.add_node("new_node", new_func)
```

**步骤 4**: 添加 Prompt 模板
```txt
# prompts/new_node.txt
你是一个专业的教学专家。请为以下主题制定教学计划：

主题: {topic}
年级: {grade}

请按照以下 JSON 格式输出：
{
    "new_field": "你的回答"
}
```

**步骤 5**: 更新 State 定义
```python
# graph/state.py
class TeachingState(TypedDict):
    topic: str
    grade: str
    plan: dict
    knowledge: dict
    design: dict
    content: dict
    final_output: dict
    new_field: dict      # 新增字段
    error_count: int
    max_retries: int
```

### 2. 修改现有节点

**安全修改原则**:
1. 保持向后兼容性
2. 不改变现有接口
3. 添加新功能而非修改旧功能
4. 充分测试修改

**示例**: 增强 planner_node
```python
# 在 planner_node.py 中添加新功能
def enhanced_planner_node(state: TeachingState) -> TeachingState:
    """增强版 planner 节点"""
    # 保留原有逻辑
    original_result = original_planner_node(state)
    
    # 添加新特性
    if "plan" in original_result and original_result["plan"]:
        # 分析计划质量
        quality_score = analyze_plan_quality(original_result["plan"])
        original_result["quality_analysis"] = {
            "score": quality_score,
            "suggestions": generate_suggestions(quality_score)
        }
    
    return original_result
```

### 3. 扩展 LLM Layer

**添加新的 LLM 提供商**:
```python
# llm/openai.py
class OpenAIClient:
    def generate_structured_output(self, prompt, schema, system_prompt):
        pass

# llm/claude.py 中支持多提供商选择
class LLMClient:
    def __init__(self, provider="claude"):
        if provider == "claude":
            self.client = get_claude_client()
        elif provider == "openai":
            self.client = OpenAIClient()
```

## 🧪 测试开发

### 1. 单元测试

```python
# tests/test_new_feature.py
import unittest
from unittest.mock import Mock, patch
from nodes.planner_node import planner_node

class TestPlannerNode(unittest.TestCase):

    def setUp(self):
        self.initial_state = {
            "topic": "二次函数",
            "grade": "高中二年级",
            "plan": {},
            "knowledge": {},
            "design": {},
            "content": {},
            "final_output": {},
            "error_count": 0,
            "max_retries": 3
        }

    @patch('nodes.planner_node.get_claude_client')
    def test_planner_node_success(self, mock_get_client):
        """测试 planner_node 成功执行"""
        # Mock Claude 客户端
        mock_client = Mock()
        mock_client.generate_structured_output.return_value = {
            "goals": [{"description": "理解概念", "difficulty": "中等", "time_required": "15分钟"}],
            "key_points": [{"name": "开口方向", "importance": "高", "prerequisites": []}],
            "difficulty_level": "中等",
            "estimated_time": "90分钟",
            "teaching_objectives": {
                "cognitive": "理解",
                "skill": "掌握",
                "attitude": "培养兴趣"
            },
            "assessment_criteria": ["准确性", "完整性"]
        }
        mock_get_client.return_value = mock_client

        # 执行测试
        result_state = planner_node(self.initial_state)

        # 验证结果
        self.assertIn("plan", result_state)
        self.assertEqual(len(result_state["plan"]["goals"]), 1)
        self.assertEqual(result_state["plan"]["difficulty_level"], "中等")

    def test_planner_node_error_handling(self):
        """测试 planner_node 的错误处理"""
        # 设置一个会导致错误的初始状态
        error_state = self.initial_state.copy()
        error_state["topic"] = ""  # 空主题会导致错误

        result_state = planner_node(error_state)

        # 验证错误处理
        self.assertIn("error", result_state["plan"])
        self.assertGreaterEqual(result_state["error_count"], 0)

if __name__ == '__main__':
    unittest.main()
```

### 2. 集成测试

```python
# tests/test_integration.py
from graph.builder import build_teaching_copilot_graph
from graph.state import create_initial_state

def test_complete_workflow():
    """测试完整的工作流"""
    # 创建工作流
    graph = build_teaching_copilot_graph()
    assert graph is not None

    # 创建初始状态
    initial_state = create_initial_state("二次函数", "高中二年级")

    # 执行工作流
    try:
        result_state = graph.invoke(initial_state)
        assert "final_output" in result_state
        assert "metadata" in result_state["final_output"]
    except Exception as e:
        print(f"工作流执行失败: {e}")
        raise
```

### 3. 性能测试

```python
# tests/test_performance.py
import time
from app import run_workflow

def test_performance():
    """测试工作流性能"""
    start_time = time.time()

    result = run_workflow("二次函数", "高中二年级")

    end_time = time.time()
    duration = end_time - start_time

    print(f"执行时间: {duration:.2f} 秒")
    print(f"API 调用次数: {result.get('api_calls', '未知')}")
    print(f"生成的文件大小: {len(str(result))} 字符")

    # 性能要求
    assert duration < 60, "执行时间过长"

if __name__ == "__main__":
    test_performance()
```

## 🔄 持续集成

### GitHub Actions 配置
```yaml
# .github/workflows/ci.yml
name: CI/CD

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest black flake8
    - name: Run tests
      run: |
        python -m pytest tests/ -v
    - name: Check code style
      run: |
        black --check .
        flake8 .
```

## 🚀 部署指南

### 1. 本地部署
```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 运行应用
python app.py --topic "二次函数" --grade "高中二年级"
```

### 2. Docker 部署
```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  teaching-copilot:
    build: .
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    ports:
      - "8000:8000"
    volumes:
      - ./output:/app/output
```

### 3. 生产部署
```bash
# 构建镜像
docker build -t teaching-copilot .

# 运行容器
docker run -d \
  --name teaching-copilot \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -v $(pwd)/output:/app/output \
  teaching-copilot
```

## 📊 监控和调试

### 1. 日志分析
```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 查看特定节点的日志
logger = logging.getLogger('nodes.planner_node')
logger.setLevel(logging.DEBUG)
```

### 2. 性能监控
```python
import time
from functools import wraps

def performance_monitor(func):
    """性能监控装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"{func.__name__} 执行时间: {duration:.3f} 秒")
        return result
    return wrapper

@performance_monitor
def slow_operation():
    time.sleep(1)
    return "完成"
```

### 3. 错误追踪
```python
import traceback

def safe_execute(func):
    """安全执行装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"函数 {func.__name__} 执行失败: {e}")
            logger.error(f"错误堆栈:\n{traceback.format_exc()}")
            # 返回默认值或重试
            return {"error": str(e), "function": func.__name__}
    return wrapper
```

## 🎯 最佳实践

### 1. 代码组织
- 保持每个文件的功能单一性
- 使用清晰的模块导入结构
- 避免循环依赖

### 2. 错误处理
- 为每个可能失败的 IO 操作添加 try-catch
- 使用有意义的错误消息
- 实现适当的降级策略

### 3. 测试覆盖
- 为目标覆盖率 >80%
- 编写边界条件测试
- 模拟外部依赖

### 4. 文档维护
- 及时更新相关文档
- 保持示例代码的最新性
- 提供清晰的 API 文档

## 🤝 协作开发

### Git 工作流
```bash
# 创建特性分支
git checkout -b feature/new-feature

# 提交更改
git add .
git commit -m "feat: 添加新功能"

# 推送并创建 PR
git push origin feature/new-feature
```

### 代码审查要点
- 代码可读性和可维护性
- 错误处理是否完善
- 测试覆盖是否充分
- 文档是否更新

这个开发指南为你提供了完整的开发流程和最佳实践，帮助你高效地参与 AI Teaching Copilot 项目的开发和维护。