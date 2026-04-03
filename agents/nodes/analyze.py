# -*- coding: utf-8 -*-
"""
问题分析节点

该节点负责分析用户的原始问题，完成以下任务：
1. 提取关键词：从问题中提取用于检索的关键词
2. 识别类别：判断问题属于哪个新闻类别（科技、财经、国际等）
3. 构建检索查询：将关键词组合成用于向量检索的查询字符串

使用 LLM 进行智能分析，支持中文问题理解。
"""

import json
import os
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from agents.state import AgentState
from utils.logger import get_logger

# 获取日志记录器
logger = get_logger(name="AnalyzeNode")


# ========== 配置 LLM ==========
# 从环境变量获取配置，设置默认值
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# 创建 LLM 实例
# temperature=0 表示输出更加确定性，适合分析任务
llm = ChatOpenAI(
    model=LLM_MODEL,
    temperature=0,  # 分析任务需要更确定的输出
    openai_api_key=OPENAI_API_KEY,
    openai_api_base=OPENAI_API_BASE
)


# ========== 系统提示词 ==========
# 定义 LLM 的角色和行为规范
SYSTEM_PROMPT = """你是一个新闻问题分析专家。你的任务是分析用户的问题，提取检索所需的信息。

你需要从用户问题中提取：
1. 关键词：用于新闻检索的核心词汇（2-5个）
2. 类别：问题所属的新闻类别

新闻类别选项：
- 头条：重大新闻、突发事件
- 社会：民生、社会事件
- 国内：中国相关新闻
- 国际：外国相关新闻
- 娱乐：明星、影视、综艺
- 体育：足球、篮球、奥运会等
- 科技：互联网、手机、AI、科技公司
- 财经：股票、经济、金融

如果没有明显的类别特征，category 返回 null。

请严格按照 JSON 格式返回结果：
{"keywords": ["关键词1", "关键词2"], "category": "类别或null"}

示例：
用户问题：华为最近有什么新产品？
返回：{"keywords": ["华为", "新产品", "发布"], "category": "科技"}

用户问题：最近股市怎么样？
返回：{"keywords": ["股市", "行情", "股票"], "category": "财经"}

用户问题：有什么好消息吗？
返回：{"keywords": ["好消息", "新闻"], "category": null}"""


async def analyze_node(state: AgentState) -> Dict[str, Any]:
    """
    问题分析节点的主函数

    该函数被 LangGraph 调用，执行问题分析逻辑：
    1. 获取用户的原始问题
    2. 调用 LLM 进行分析
    3. 解析 LLM 返回的 JSON 结果
    4. 构建检索查询字符串
    5. 更新循环计数

    参数:
        state: 当前 Agent 状态，包含用户的原始问题等信息

    返回:
        状态更新字典，包含以下字段：
        - keywords: 提取的关键词列表
        - category: 识别的类别（可能为 None）
        - search_query: 检索查询字符串
        - loop_count: 更新后的循环次数
    """
    # 获取用户原始问题
    query = state["query"]

    # 获取当前循环次数，默认为 0
    loop_count = state.get("loop_count", 0)

    logger.info(f"开始分析问题: {query} (第 {loop_count + 1} 次循环)")

    try:
        # ========== 调用 LLM 进行分析 ==========
        # 构建消息列表
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=query)
        ]

        # 异步调用 LLM
        response = await llm.ainvoke(messages)

        # 获取 LLM 返回的文本内容
        content = response.content.strip()
        logger.debug(f"LLM 原始返回: {content}")

        # ========== 解析 JSON 结果 ==========
        # 尝试从返回内容中提取 JSON
        # 有时 LLM 会返回带 markdown 代码块的 JSON，需要处理
        if "```json" in content:
            # 提取 markdown 代码块中的 JSON
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            # 提取普通代码块中的 JSON
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            # 直接使用返回内容
            json_str = content

        # 解析 JSON
        result = json.loads(json_str)

        # 提取关键词和类别
        keywords = result.get("keywords", [])
        category = result.get("category")

        # 确保关键词是列表类型
        if isinstance(keywords, str):
            keywords = [keywords]

        logger.info(f"分析结果 - 关键词: {keywords}, 类别: {category}")

    except json.JSONDecodeError as e:
        # JSON 解析失败，使用简单分词作为后备方案
        logger.error(f"JSON 解析失败: {e}, 使用后备方案")
        # 简单分词：按空格和标点分割
        keywords = [word for word in query.split() if len(word) > 1][:5]
        category = None

    except Exception as e:
        # 其他异常，记录错误并使用后备方案
        logger.error(f"分析问题失败: {e}")
        keywords = [query][:5]  # 直接使用原始问题作为关键词
        category = None

    # ========== 构建检索查询 ==========
    # 将关键词组合成检索字符串
    search_query = " ".join(keywords)

    # 如果是重试（loop_count > 0），扩展查询词以获取更多结果
    if loop_count > 0:
        search_query = f"{search_query} 新闻 资讯"
        logger.info(f"重试模式，扩展查询词: {search_query}")

    # ========== 返回状态更新 ==========
    # 返回的字典会被合并到当前状态中
    return {
        "keywords": keywords,
        "category": category,
        "search_query": search_query,
        "loop_count": loop_count + 1  # 更新循环次数
    }
