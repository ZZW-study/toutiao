# -*- coding: utf-8 -*-
"""新闻问答 Agent 模块导出。"""

from agents.graph import app as agent_app  # 从 agents.graph 模块导入当前文件后续要用到的对象
from agents.graph import get_agent_runner  # 从 agents.graph 模块导入当前文件后续要用到的对象

__all__ = ["agent_app", "get_agent_runner"]  # 把右边计算出来的结果保存到 __all__ 变量中，方便后面的代码继续复用

