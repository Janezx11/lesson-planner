# AI Teaching Copilot（智能教学助手）

一个基于 LangGraph 和 Claude 的面向教师的 AI 系统，可以根据教学主题自动生成完整的教学方案。

## 项目特性

- 🎯 多阶段教学方案设计
- 🧠 知识点深度分析
- 📊 结构化 JSON 输出
- 🔧 模块化 LangGraph 架构
- 🛡️ 完善的错误处理机制

## 技术栈

- Python 3.9+
- LangGraph
- Multiple LLM Providers (Claude, Qwen, LongCat)
- Pydantic (类型安全)
- Structured Output

## 快速开始

```bash
pip install -r requirements.txt
python app.py --topic "二次函数" --grade "高中二年级"
```

## 项目结构

```
lesson-planner/
├── app.py                 # 主应用入口
├── graph/
│   ├── state.py          # State 定义
│   └── builder.py        # LangGraph 工作流构建器
├── nodes/
│   ├── planner_node.py   # 规划节点
│   ├── knowledge_node.py # 知识节点
│   ├── design_node.py    # 设计节点
│   ├── content_node.py   # 内容节点
│   └── formatter_node.py # 格式化节点
├── llm/
│   ├── base.py           # LLM 基础抽象层
│   ├── claude.py         # Claude API 封装
│   ├── qwen.py           # Qwen API 封装
│   └── longcat.py        # LongCat API 封装
├── prompts/              # Prompt 模板
│   ├── planner.txt
│   ├── knowledge.txt
│   ├── design.txt
│   ├── content.txt
│   └── formatter.txt
├── utils/
│   └── parser.py         # 解析工具
└── tests/               # 测试文件
```

## 核心功能

1. **planner_node**: 拆解教学任务，生成教学目标、知识点列表、难度等级
2. **knowledge_node**: 分析知识结构，识别核心概念、易错点、前置知识
3. **design_node**: 设计教学流程，包括导入、讲解、互动、练习、总结
4. **content_node**: 生成具体教学内容，提供例题、讲解、互动问题
5. **formatter_node**: 汇总所有信息，输出最终结构化 JSON

## State 设计

```python
class TeachingState(TypedDict):
    topic: str           # 教学主题
    grade: str          # 年级
    plan: dict          # 教学计划
    knowledge: dict    # 知识结构
    design: dict       # 教学设计
    content: dict      # 教学内容
    final_output: dict # 最终输出
```

## 示例输出

```json
{
  "topic": "二次函数",
  "grade": "高中二年级",
  "plan": {
    "goals": ["理解二次函数基本概念", "掌握图像性质"],
    "key_points": ["开口方向", "对称轴", "顶点坐标"],
    "difficulty": "中等"
  },
  ...
}
```

## 开发说明

本项目采用模块化设计，每个节点独立实现，便于扩展和维护。预留了 RAG 和 tool 调用接口，为未来功能扩展做准备。