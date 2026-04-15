# -*- coding: utf-8 -*-
"""回答生成节点。"""

from __future__ import annotations  # 开启延迟解析类型注解，避免前向引用在导入阶段就被过早求值

from typing import Any  # 从 typing 模块导入当前文件后续要用到的对象

from agents.services import get_generate_service  # 从 agents.services 模块导入当前文件后续要用到的对象
from agents.state import AgentState  # 从 agents.state 模块导入当前文件后续要用到的对象

MAX_AGENT_LOOPS = 3  # 把这个常量值保存到 MAX_AGENT_LOOPS 中，后面会作为固定配置反复使用


async def generate_node(state: AgentState) -> dict[str, Any]:  # 定义异步函数 generate_node，调用它时通常需要配合 await 使用
    """根据检索结果生成最终回答。"""

    result = await get_generate_service().generate(  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用
        query=state["query"],  # 把右边计算出来的结果保存到 query 变量中，方便后面的代码继续复用
        news_list=state.get("news_list", []),  # 把右边计算出来的结果保存到 news_list 变量中，方便后面的代码继续复用
        loop_count=state.get("loop_count", 1),  # 把右边计算出来的结果保存到 loop_count 变量中，方便后面的代码继续复用
        max_loops=MAX_AGENT_LOOPS,  # 把右边计算出来的结果保存到 max_loops 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    return {  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
        "answer": result.answer,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        "is_satisfied": result.is_satisfied,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    }  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

