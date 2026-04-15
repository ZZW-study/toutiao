# -*- coding: utf-8 -*-
"""新闻检索节点。"""

from __future__ import annotations  # 开启延迟解析类型注解，避免前向引用在导入阶段就被过早求值

from typing import Any  # 从 typing 模块导入当前文件后续要用到的对象

from agents.state import AgentState  # 从 agents.state 模块导入当前文件后续要用到的对象
from agents.tools.news_retriever import get_news_retriever_service  # 从 agents.tools.news_retriever 模块导入当前文件后续要用到的对象


async def retrieve_node(state: AgentState) -> dict[str, Any]:  # 定义异步函数 retrieve_node，调用它时通常需要配合 await 使用
    """根据分析结果检索新闻。"""

    loop_count = state.get("loop_count", 1)  # 把右边计算出来的结果保存到 loop_count 变量中，方便后面的代码继续复用
    top_k = min(5 + max(loop_count - 1, 0) * 2, 15)  # 把右边计算出来的结果保存到 top_k 变量中，方便后面的代码继续复用
    news_list = await get_news_retriever_service().search_news(  # 把右边计算出来的结果保存到 news_list 变量中，方便后面的代码继续复用
        query=state.get("search_query", ""),  # 把右边计算出来的结果保存到 query 变量中，方便后面的代码继续复用
        category=state.get("category"),  # 把右边计算出来的结果保存到 category 变量中，方便后面的代码继续复用
        top_k=top_k,  # 把右边计算出来的结果保存到 top_k 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    return {"news_list": news_list}  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

