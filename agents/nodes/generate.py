# -*- coding: utf-8 -*-
"""
回答生成节点

该节点负责基于检索到的新闻生成最终回答，完成以下任务：
1. 构建上下文：将检索到的新闻格式化为上下文文本
2. 调用 LLM：基于上下文生成回答
3. 质量评估：判断回答是否充分，决定是否需要重试

回答生成的核心是 RAG（检索增强生成）模式：
- 以检索到的新闻作为知识来源
- 让 LLM 基于事实生成回答，避免幻觉
"""

import json
import os
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from agents.state import AgentState
from utils.logger import get_logger

# 获取日志记录器
logger = get_logger(name="GenerateNode")


# ========== 配置 LLM ==========
# 从环境变量获取配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# 创建 LLM 实例
# temperature=0.3 让回答有一定的创造性，但仍然基于事实
llm = ChatOpenAI(
    model=LLM_MODEL,
    temperature=0.3,  # 生成任务可以稍微有创造性
    openai_api_key=OPENAI_API_KEY,
    openai_api_base=OPENAI_API_BASE
)


# ========== 系统提示词 ==========
# 定义 LLM 的角色和输出格式
SYSTEM_PROMPT = """你是一个专业的新闻助手。你的任务是基于检索到的新闻回答用户问题。

要求：
1. 只基于提供的新闻内容回答，不要编造信息
2. 回答要简洁、准确、有条理
3. 如果新闻内容不足以回答问题，如实告知用户
4. 引用新闻时可以提及新闻标题

同时，你需要判断回答是否充分：
- 充分：回答内容能够解答用户问题，且相关性强
- 不充分：找不到相关新闻，或新闻内容与问题关联不大

请严格按照 JSON 格式返回：
{
    "answer": "你的回答内容",
    "is_satisfied": true/false
}

示例回答格式：
{
    "answer": "根据最近的新闻，华为发布了新款手机 Mate 60 系列，搭载了自研芯片。",
    "is_satisfied": true
}

如果新闻不足：
{
    "answer": "抱歉，目前没有找到与您问题直接相关的新闻。",
    "is_satisfied": false
}"""


def build_context(news_list: list[dict], max_length: int = 2000) -> str:
    """
    构建上下文文本

    将检索到的新闻列表格式化为 LLM 可理解的上下文文本。
    包含新闻标题和内容摘要。

    参数:
        news_list: 新闻列表，每条新闻是一个字典
        max_length: 上下文最大长度（字符数），避免超出 LLM 上下文限制

    返回:
        格式化后的上下文字符串
    """
    if not news_list:
        return "没有找到相关新闻。"

    context_parts = []
    total_length = 0

    for i, news in enumerate(news_list, 1):
        # 构建单条新闻的文本
        title = news.get("title", "无标题")
        content = news.get("content", "")[:500]  # 限制单条新闻内容长度

        news_text = f"【新闻{i}】标题：{title}\n内容：{content}\n"

        # 检查总长度是否超限
        if total_length + len(news_text) > max_length:
            break

        context_parts.append(news_text)
        total_length += len(news_text)

    return "\n".join(context_parts)


async def generate_node(state: AgentState) -> Dict[str, Any]:
    """
    回答生成节点的主函数

    该函数被 LangGraph 调用，执行回答生成逻辑：
    1. 获取用户问题和检索到的新闻
    2. 构建包含新闻上下文的提示词
    3. 调用 LLM 生成回答
    4. 解析 LLM 返回结果，提取回答和质量判断

    参数:
        state: 当前 Agent 状态，包含 query、news_list 等字段

    返回:
        状态更新字典，包含以下字段：
        - answer: 生成的回答文本
        - is_satisfied: 回答是否充分
    """
    # 获取用户原始问题
    query = state["query"]

    # 获取检索到的新闻列表
    news_list = state.get("news_list", [])

    # 获取循环次数
    loop_count = state.get("loop_count", 1)

    logger.info(f"开始生成回答 - 问题: '{query}', 新闻数: {len(news_list)}")

    # ========== 快速处理：没有新闻的情况 ==========
    if not news_list:
        logger.warning("没有检索到任何新闻，返回默认回答")
        return {
            "answer": "抱歉，目前没有找到与您问题相关的新闻。请尝试换个问题或稍后再问。",
            "is_satisfied": False
        }

    # ========== 构建上下文 ==========
    # 将新闻列表格式化为上下文文本
    context = build_context(news_list)
    logger.debug(f"构建上下文完成，长度: {len(context)} 字符")

    # ========== 构建用户提示词 ==========
    user_prompt = f"""用户问题：{query}

以下是检索到的相关新闻：

{context}

请基于以上新闻回答用户问题，并以 JSON 格式返回结果。"""

    try:
        # ========== 调用 LLM 生成回答 ==========
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]

        response = await llm.ainvoke(messages)
        content = response.content.strip()

        logger.debug(f"LLM 原始返回: {content[:200]}...")

        # ========== 解析 JSON 结果 ==========
        # 处理可能存在的 markdown 代码块
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content

        result = json.loads(json_str)

        # 提取回答和质量判断
        answer = result.get("answer", "")
        is_satisfied = result.get("is_satisfied", True)

        logger.info(f"回答生成完成 - 充分: {is_satisfied}")

        # 如果是重试且仍然不满意，降低期望
        if not is_satisfied and loop_count >= 3:
            logger.info("已达最大循环次数，强制标记为满意")
            is_satisfied = True

    except json.JSONDecodeError as e:
        # JSON 解析失败，直接使用 LLM 返回的文本作为回答
        logger.error(f"JSON 解析失败: {e}")
        answer = content if content else "抱歉，生成回答时出现问题。"
        is_satisfied = True  # 避免无限循环

    except Exception as e:
        # 其他异常处理
        logger.error(f"生成回答失败: {e}")
        answer = f"抱歉，生成回答时出现错误: {str(e)}"
        is_satisfied = True  # 避免无限循环

    # ========== 返回状态更新 ==========
    return {
        "answer": answer,
        "is_satisfied": is_satisfied
    }
