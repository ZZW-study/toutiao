# -*- coding: utf-8 -*-
"""Agent 工作流入口。"""

from __future__ import annotations  # 开启延迟解析类型注解，避免前向引用在导入阶段就被过早求值

import asyncio  # 导入 asyncio 模块，给当前文件后面的逻辑使用
from typing import Any  # 从 typing 模块导入当前文件后续要用到的对象

from langgraph.graph import END, StateGraph  # 从 langgraph.graph 模块导入当前文件后续要用到的对象

from agents.nodes.analyze import analyze_node  # 从 agents.nodes.analyze 模块导入当前文件后续要用到的对象
from agents.nodes.generate import generate_node  # 从 agents.nodes.generate 模块导入当前文件后续要用到的对象
from agents.nodes.retrieve import retrieve_node  # 从 agents.nodes.retrieve 模块导入当前文件后续要用到的对象
from agents.state import AgentState  # 从 agents.state 模块导入当前文件后续要用到的对象
from utils.logger import get_logger  # 从 utils.logger 模块导入当前文件后续要用到的对象

logger = get_logger(name="AgentGraph")  # 把右边计算出来的结果保存到 logger 变量中，方便后面的代码继续复用


def should_continue(state: AgentState) -> str:  # 定义函数 should_continue，把一段可以复用的逻辑单独封装起来
    """决定是结束还是继续重试。"""

    if state.get("is_satisfied", False):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return "end"  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    if state.get("loop_count", 0) >= 3:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return "end"  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    return "retry"  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


class NewsQaAgentRunner:  # 定义 NewsQaAgentRunner 类，用来把这一块相关的状态和行为组织在一起
    """延迟构建的新闻问答 Agent。

    这里保留 LangGraph 的编排优势，但去掉了模块导入时的全局初始化和未实际使用的
    `MemorySaver`，让 Web 应用和 AI 栈的耦合更小。
    """

    def __init__(self) -> None:  # 定义函数 __init__，把一段可以复用的逻辑单独封装起来
        """初始化 Runner，并准备延迟构建工作流所需的内部状态。"""
        self._graph = None  # 把右边计算出来的结果保存到 _graph 变量中，方便后面的代码继续复用
        self._build_lock = asyncio.Lock()  # 把右边计算出来的结果保存到 _build_lock 变量中，方便后面的代码继续复用

    def _build_graph_sync(self):  # 定义函数 _build_graph_sync，把一段可以复用的逻辑单独封装起来
        """同步构建 LangGraph 工作流，把节点和边一次性串起来。"""
        workflow = StateGraph(AgentState)  # 把右边计算出来的结果保存到 workflow 变量中，方便后面的代码继续复用
        workflow.add_node("analyze", analyze_node)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        workflow.add_node("retrieve", retrieve_node)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        workflow.add_node("generate", generate_node)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        workflow.set_entry_point("analyze")  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        workflow.add_edge("analyze", "retrieve")  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        workflow.add_edge("retrieve", "generate")  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        workflow.add_conditional_edges(  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            "generate",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            should_continue,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            {"end": END, "retry": "analyze"},  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
        logger.info("新闻问答 Agent 工作流已构建")  # 记录一条日志，方便后续排查程序运行过程和定位问题
        return workflow.compile()  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    async def _get_graph(self):  # 定义异步函数 _get_graph，调用它时通常需要配合 await 使用
        """懒加载并返回编译后的工作流实例。"""
        if self._graph is not None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return self._graph  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        async with self._build_lock:  # 以异步上下文管理的方式使用资源，结束时会自动做清理
            if self._graph is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                self._graph = self._build_graph_sync()  # 把右边计算出来的结果保存到 _graph 变量中，方便后面的代码继续复用
        return self._graph  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    async def ainvoke(  # 定义异步函数 ainvoke，调用它时通常需要配合 await 使用
        self,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        initial_state: dict[str, Any],  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        session_id: str | None = None,  # 把右边计算出来的结果保存到 session_id 变量中，方便后面的代码继续复用
    ) -> dict[str, Any]:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
        """执行工作流。

        目前没有引入会话级 Memory，因此 `session_id` 先保留为兼容参数。
        """

        graph = await self._get_graph()  # 把右边计算出来的结果保存到 graph 变量中，方便后面的代码继续复用
        return await graph.ainvoke(initial_state)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


_agent_runner: NewsQaAgentRunner | None = None  # 把右边计算出来的结果保存到 _agent_runner 变量中，方便后面的代码继续复用


def get_agent_runner() -> NewsQaAgentRunner:  # 定义函数 get_agent_runner，把一段可以复用的逻辑单独封装起来
    """返回全局唯一的 Agent Runner。"""
    global _agent_runner  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    if _agent_runner is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        _agent_runner = NewsQaAgentRunner()  # 把右边计算出来的结果保存到 _agent_runner 变量中，方便后面的代码继续复用
    return _agent_runner  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


def create_agent_graph() -> NewsQaAgentRunner:  # 定义函数 create_agent_graph，把一段可以复用的逻辑单独封装起来
    """兼容旧接口。"""

    return get_agent_runner()  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


app = get_agent_runner()  # 把右边计算出来的结果保存到 app 变量中，方便后面的代码继续复用
