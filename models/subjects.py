"""
学科模板系统

为不同学科提供定制化的教学指导，注入到各节点的 prompt 中。

使用方式：
    from models.subjects import get_subject_guidance, detect_subject
    subject = detect_subject(topic)
    guidance = get_subject_guidance(subject)
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SubjectGuidance:
    """学科教学指导"""
    name: str
    display_name: str

    # planner_node: 推荐的认知阶段类型
    preferred_stages: list = field(default_factory=list)

    # planner_node: 推荐的教学策略
    preferred_strategies: list = field(default_factory=list)

    # knowledge_node: 知识结构分析重点
    knowledge_focus: str = ""

    # content_node: 练习题设计指导
    question_tips: str = ""

    # compiler_node: 教学目标常用动词
    objective_verbs: list = field(default_factory=list)

    # 通用补充提示
    extra_tips: str = ""


# 学科注册表
SUBJECTS: dict[str, SubjectGuidance] = {
    "数学": SubjectGuidance(
        name="数学",
        display_name="数学",
        preferred_stages=["认知冲突", "规律发现", "模型建构", "迁移应用"],
        preferred_strategies=["类比教学", "直观演示", "对比分析"],
        knowledge_focus="重点关注：概念定义的精确性、公式的推导过程、数形结合思想、数学建模能力。",
        question_tips="练习题应包含：计算题（带完整步骤）、证明题、应用题。注意一题多解和变式训练。",
        objective_verbs=["计算", "推导", "证明", "求解", "画出", "分析", "建立"],
        extra_tips="数学课要注重'从具体到抽象'的认知过程，多用图形、表格辅助理解。",
    ),
    "物理": SubjectGuidance(
        name="物理",
        display_name="物理",
        preferred_stages=["认知冲突", "实践验证", "模型建构", "迁移应用"],
        preferred_strategies=["直观演示", "案例分析", "任务驱动"],
        knowledge_focus="重点关注：物理概念的物理意义、定律的适用条件、实验设计思路、物理建模能力。",
        question_tips="练习题应包含：概念辨析题、计算题（含受力分析/过程分析）、实验题、综合应用题。",
        objective_verbs=["描述", "解释", "计算", "设计", "分析", "测量", "验证"],
        extra_tips="物理课要重视实验演示和生活实例，帮助学生建立物理图景。",
    ),
    "化学": SubjectGuidance(
        name="化学",
        display_name="化学",
        preferred_stages=["认知冲突", "规律发现", "实践验证", "模型建构"],
        preferred_strategies=["直观演示", "案例分析", "小组探究"],
        knowledge_focus="重点关注：化学方程式书写、反应原理、实验操作规范、微观与宏观的联系。",
        question_tips="练习题应包含：方程式书写、实验现象描述、计算题（物质的量等）、推断题。",
        objective_verbs=["写出", "描述", "解释", "计算", "设计", "区分", "配平"],
        extra_tips="化学课要注重实验安全教育，强调'宏观现象—微观解释—符号表征'三重表征。",
    ),
    "生物": SubjectGuidance(
        name="生物",
        display_name="生物",
        preferred_stages=["规律发现", "案例分析", "模型建构", "迁移应用"],
        preferred_strategies=["案例分析", "小组探究", "直观演示"],
        knowledge_focus="重点关注：核心概念（如细胞、遗传、进化）、生命系统的层次结构、实验探究能力。",
        question_tips="练习题应包含：概念填空、识图分析、实验设计、信息获取与分析。",
        objective_verbs=["描述", "解释", "比较", "分析", "设计", "绘制", "归纳"],
        extra_tips="生物课要联系生活实际，多用图片、视频展示微观生命过程。",
    ),
    "语文": SubjectGuidance(
        name="语文",
        display_name="语文",
        preferred_stages=["认知冲突", "案例分析", "规律发现", "迁移应用"],
        preferred_strategies=["案例分析", "类比教学", "对比分析"],
        knowledge_focus="重点关注：文本解读能力、语言表达能力、文学鉴赏能力、写作技巧。",
        question_tips="练习题应包含：阅读理解、词语运用、写作练习、口语交际。注意分层设计。",
        objective_verbs=["分析", "概括", "鉴赏", "评价", "写作", "表达", "比较"],
        extra_tips="语文课要注重朗读、讨论、写作的有机结合，培养语感和思维能力。",
    ),
    "英语": SubjectGuidance(
        name="英语",
        display_name="英语",
        preferred_stages=["认知冲突", "规律发现", "迁移应用", "实践验证"],
        preferred_strategies=["类比教学", "任务驱动", "对比分析"],
        knowledge_focus="重点关注：语法规则的准确性、词汇的语境运用、听说读写综合能力。",
        question_tips="练习题应包含：语法填空、阅读理解、写作练习、口语对话。注意真实语境设计。",
        objective_verbs=["识别", "运用", "翻译", "描述", "编写", "比较", "总结"],
        extra_tips="英语课要创设真实语言情境，多用图片、音频、视频辅助教学。",
    ),
    "历史": SubjectGuidance(
        name="历史",
        display_name="历史",
        preferred_stages=["认知冲突", "案例分析", "规律发现", "迁移应用"],
        preferred_strategies=["案例分析", "对比分析", "类比教学"],
        knowledge_focus="重点关注：历史事件的因果关系、历史人物的评价方法、史料分析能力、唯物史观。",
        question_tips="练习题应包含：史料分析题、论述题、比较题、材料解析题。",
        objective_verbs=["描述", "分析", "评价", "比较", "归纳", "论证", "解释"],
        extra_tips="历史课要注重史料教学，培养学生'论从史出'的思维方法。",
    ),
    "地理": SubjectGuidance(
        name="地理",
        display_name="地理",
        preferred_stages=["认知冲突", "规律发现", "模型建构", "迁移应用"],
        preferred_strategies=["直观演示", "案例分析", "对比分析"],
        knowledge_focus="重点关注：地理要素的相互关系、人地协调观、区域认知能力、地理实践力。",
        question_tips="练习题应包含：读图分析、区域比较、综合分析、实践调查。",
        objective_verbs=["描述", "解释", "分析", "绘制", "比较", "归纳", "评价"],
        extra_tips="地理课要多用地图、遥感影像、GIS等工具，培养空间思维能力。",
    ),
    "信息技术": SubjectGuidance(
        name="信息技术",
        display_name="信息技术",
        preferred_stages=["认知冲突", "实践验证", "迁移应用", "模型建构"],
        preferred_strategies=["任务驱动", "直观演示", "小组探究"],
        knowledge_focus="重点关注：算法思维、数据结构、编程逻辑、信息安全意识、数字化学习能力。",
        question_tips="练习题应包含：编程题、算法分析题、操作题、方案设计题。",
        objective_verbs=["编写", "设计", "分析", "调试", "优化", "解释", "应用"],
        extra_tips="信息技术课要注重实践操作，采用'做中学'的教学方式。",
    ),
    "政治": SubjectGuidance(
        name="政治",
        display_name="政治",
        preferred_stages=["认知冲突", "案例分析", "规律发现", "迁移应用"],
        preferred_strategies=["案例分析", "对比分析", "任务驱动"],
        knowledge_focus="重点关注：核心概念的理解、理论联系实际、辩证思维能力、价值判断能力。",
        question_tips="练习题应包含：材料分析题、论述题、辨析题、时政评论。",
        objective_verbs=["分析", "评价", "论证", "说明", "比较", "归纳", "运用"],
        extra_tips="政治课要联系时事热点，引导学生关注社会、参与社会实践。",
    ),
}

# 主题 → 学科 的关键词映射
_SUBJECT_KEYWORDS: dict[str, list[str]] = {
    "数学": ["函数", "方程", "几何", "代数", "概率", "统计", "三角", "向量", "数列", "导数", "积分", "集合", "不等式", "矩阵", "二次函数", "一次函数", "抛物线", "圆", "三角形"],
    "物理": ["力学", "电学", "光学", "热学", "磁", "牛顿", "加速度", "速度", "能量", "动量", "电场", "磁场", "电磁感应", "电路", "波动", "原子", "核"],
    "化学": ["化学", "元素", "分子", "原子", "反应", "溶液", "酸碱", "氧化", "有机", "电解", "离子", "化学键", "化学方程式"],
    "生物": ["细胞", "基因", "遗传", "进化", "生态", "光合作用", "呼吸作用", "蛋白质", "DNA", "RNA", "染色体", "生物", "器官", "组织"],
    "语文": ["作文", "阅读", "古诗", "文言文", "修辞", "语法", "文学", "小说", "散文", "诗歌", "戏剧", "议论文", "记叙文", "说明文"],
    "英语": ["语法", "时态", "词汇", "阅读", "写作", "听力", "口语", "从句", "虚拟语气", "被动语态", "现在进行时", "过去完成时"],
    "历史": ["历史", "朝代", "革命", "改革", "战争", "文明", "制度", "条约", "运动", "起义"],
    "地理": ["气候", "地形", "河流", "洋流", "板块", "人口", "城市", "农业", "工业", "资源", "环境", "区域"],
    "信息技术": ["编程", "算法", "数据", "网络", "计算机", "软件", "硬件", "数据库", "人工智能", "Python", "Java", "分层", "协议", "IP"],
    "政治": ["经济", "政治", "哲学", "法律", "民主", "权利", "义务", "市场", "宏观调控", "唯物辩证"],
}


def detect_subject(topic: str) -> Optional[str]:
    """根据教学主题自动检测学科。

    Args:
        topic: 教学主题（如"二次函数"、"牛顿第二定律"）

    Returns:
        学科名称，无法识别时返回 None
    """
    topic_lower = topic.lower()
    scores = {}
    for subject, keywords in _SUBJECT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in topic or kw.lower() in topic_lower)
        if score > 0:
            scores[subject] = score

    if not scores:
        return None
    return max(scores, key=scores.get)


def get_subject_guidance(subject_name: Optional[str]) -> Optional[SubjectGuidance]:
    """获取学科教学指导。

    Args:
        subject_name: 学科名称（如"数学"），None 时返回 None

    Returns:
        SubjectGuidance 实例，未找到时返回 None
    """
    if not subject_name:
        return None
    return SUBJECTS.get(subject_name)


def format_subject_guidance(guidance: Optional[SubjectGuidance]) -> str:
    """将学科指导格式化为可注入 prompt 的文本。

    Args:
        guidance: SubjectGuidance 实例

    Returns:
        格式化的指导文本，无指导时返回空字符串
    """
    if not guidance:
        return ""

    lines = [
        f"【学科特定指导 — {guidance.display_name}】",
        "",
    ]

    if guidance.preferred_stages:
        lines.append(f"推荐认知阶段：{'、'.join(guidance.preferred_stages)}")

    if guidance.preferred_strategies:
        lines.append(f"推荐教学策略：{'、'.join(guidance.preferred_strategies)}")

    if guidance.knowledge_focus:
        lines.append(f"\n{guidance.knowledge_focus}")

    if guidance.question_tips:
        lines.append(f"\n{guidance.question_tips}")

    if guidance.objective_verbs:
        lines.append(f"\n教学目标常用动词：{'、'.join(guidance.objective_verbs)}")

    if guidance.extra_tips:
        lines.append(f"\n{guidance.extra_tips}")

    return "\n".join(lines)
