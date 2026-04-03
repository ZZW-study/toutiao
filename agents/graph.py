# -*- coding: utf-8 -*-
"""
LangGraph 编排入口

该文件定义了新闻问答 Agent 的完整工作流程，使用 LangGraph 进行编排。

工作流程：
用户问题 → 问题分析 → 新闻检索 → 回答生成 → 判断是否充分
                                              ↓
                                        充分 → 结束
                                        不充分 → 返回问题分析（最多3次）

图结构：
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │  analyze │───▶│ retrieve │───▶│ generate │
    │ (问题分析) │    │ (新闻检索) │    │ (回答生成) │
    └──────────┘    └──────────┘    └──────────┘
         ▲                               │
         └───────────────────────────────┘
              (回答不充分时循环重试)
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agents.state import AgentState
from agents.nodes.analyze import analyze_node
from agents.nodes.retrieve import retrieve_node
from agents.nodes.generate import generate_node
from utils.logger import get_logger

# 获取日志记录器
logger = get_logger(name="AgentGraph")


def should_continue(state: AgentState) -> str:
    """
    判断是否继续循环的条件函数

    该函数在 generate 节点执行后调用，决定是结束工作流还是继续循环。

    判断逻辑：
    1. 如果回答已经充分 (is_satisfied=True)，结束工作流
    2. 如果循环次数已达到上限（3次），结束工作流
    3. 否则，返回 analyze 节点重新分析问题

    参数:
        state: 当前 Agent 状态

    返回:
        "end": 结束工作流
        "retry": 继续循环，返回 analyze 节点
    """
    # 检查回答是否充分
    if state.get("is_satisfied", False):
        logger.info("回答已充分，结束工作流")
        return "end"

    # 检查循环次数是否超过上限
    loop_count = state.get("loop_count", 0)
    if loop_count >= 3:
        logger.warning(f"循环次数已达上限 ({loop_count}次)，强制结束工作流")
        return "end"

    # 继续循环
    logger.info(f"回答不充分，开始第 {loop_count + 1} 次循环")
    return "retry"


def create_agent_graph():
    """
    创建并编译 Agent 工作流图

    该函数使用 LangGraph 的 StateGraph 构建工作流图：
    1. 添加三个节点：analyze、retrieve、generate
    2. 设置入口点为 analyze
    3. 定义节点间的边
    4. 添加条件边实现循环逻辑
    5. 编译图并返回可执行的应用

    返回:
        编译后的 LangGraph 应用，可以直接调用 ainvoke 执行
    """
    logger.info("开始创建 Agent 工作流图")

    # 创建状态图，使用 AgentState 作为状态类型
    workflow = StateGraph(AgentState)

    # ========== 添加节点 ==========
    # 每个节点是一个异步函数，接收状态并返回状态更新
    workflow.add_node("analyze", analyze_node)      # 问题分析节点
    workflow.add_node("retrieve", retrieve_node)    # 新闻检索节点
    workflow.add_node("generate", generate_node)    # 回答生成节点

    logger.debug("已添加 3 个节点：analyze, retrieve, generate")

    # ========== 设置入口点 ==========
    # 用户输入首先进入 analyze 节点
    workflow.set_entry_point("analyze")

    # ========== 添加普通边 ==========
    # analyze → retrieve：问题分析完成后检索新闻
    workflow.add_edge("analyze", "retrieve")

    # retrieve → generate：检索完成后生成回答
    workflow.add_edge("retrieve", "generate")

    logger.debug("已添加普通边：analyze → retrieve → generate")

    # ========== 添加条件边 ==========
    # generate 节点执行后，根据 should_continue 的返回值决定下一步
    # - "end" → 结束工作流
    # - "retry" → 返回 analyze 节点重新分析
    workflow.add_conditional_edges(
        "generate",           # 条件边的起始节点
        should_continue,      # 条件判断函数
        {
            "end": END,       # 结束
            "retry": "analyze"  # 重试，返回分析节点
        }
    )

    logger.debug("已添加条件边：generate → END/analyze")

    # ========== 编译图 ==========
    # MemorySaver 用于保存工作流状态，支持暂停/恢复等高级功能
    # 这里主要用于日志记录和调试
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)

    logger.info("Agent 工作流图创建完成")

    return app


# 创建全局的 Agent 应用实例
# 其他模块可以通过 from agents.graph import app 来使用
app = create_agent_graph()
