# -*- coding: utf-8 -*-
"""聊天路由测试。"""

from __future__ import annotations  # 开启延迟解析类型注解，避免前向引用在导入阶段就被过早求值

import pytest  # 导入 pytest 模块，给当前文件后面的逻辑使用
from httpx import AsyncClient  # 从 httpx 模块导入当前文件后续要用到的对象

import indexer  # 导入 indexer 模块，给当前文件后面的逻辑使用
import routers.chat as chat_router  # 导入 routers.chat as chat_router 模块，给当前文件后面的逻辑使用


class _FakeAgentRunner:  # 定义 _FakeAgentRunner 类，用来把这一块相关的状态和行为组织在一起
    """用假的 Agent Runner 替代真实工作流，方便隔离聊天路由测试。"""
    def __init__(self, result=None, error: Exception | None = None):  # 定义函数 __init__，把一段可以复用的逻辑单独封装起来
        """初始化测试用的返回值或异常对象。"""
        self._result = result or {}  # 把右边计算出来的结果保存到 _result 变量中，方便后面的代码继续复用
        self._error = error  # 把右边计算出来的结果保存到 _error 变量中，方便后面的代码继续复用

    async def ainvoke(self, initial_state, session_id=None):  # 定义异步函数 ainvoke，调用它时通常需要配合 await 使用
        """模拟 Agent 的异步执行接口，按测试需要返回结果或抛错。"""
        if self._error is not None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            raise self._error  # 主动抛出异常，让上层知道这里出现了需要处理的问题
        return self._result  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_chat_success(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):  # 定义异步函数 test_chat_success，调用它时通常需要配合 await 使用
    """聊天接口应返回标准化回答结构。"""

    monkeypatch.setattr(  # 使用 monkeypatch 临时替换依赖，避免测试时真的访问外部组件
        chat_router,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        "get_agent_runner",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        lambda: _FakeAgentRunner(  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            {  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                "answer": "这是基于检索结果整理出的回答。",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                "loop_count": 1,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                "news_list": [  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                    {  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                        "id": 1,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                        "title": "测试新闻",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                        "content": "测试内容",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                        "description": "测试摘要",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                        "category_id": 1,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                        "publish_time": "2024-01-01T00:00:00",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                        "image": None,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                        "author": "测试作者",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                    }  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
                ],  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
            }  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
        ),  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

    response = await client.post("/chat/", json={"query": "帮我总结一下今天的新闻"})  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
    assert response.status_code == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    data = response.json()  # 把右边计算出来的结果保存到 data 变量中，方便后面的代码继续复用
    assert data["answer"] == "这是基于检索结果整理出的回答。"  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert data["loop_count"] == 1  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert len(data["news_list"]) == 1  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert data["news_list"][0]["title"] == "测试新闻"  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_chat_failure_returns_500(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):  # 定义异步函数 test_chat_failure_returns_500，调用它时通常需要配合 await 使用
    """Agent 异常时应返回 500。"""

    monkeypatch.setattr(  # 使用 monkeypatch 临时替换依赖，避免测试时真的访问外部组件
        chat_router,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        "get_agent_runner",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        lambda: _FakeAgentRunner(error=RuntimeError("agent failed")),  # 把右边计算出来的结果保存到 lambda 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

    response = await client.post("/chat/", json={"query": "测试异常路径"})  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
    assert response.status_code == 500  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    data = response.json()  # 把右边计算出来的结果保存到 data 变量中，方便后面的代码继续复用
    assert data["code"] == 500  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert "处理请求失败" in data["message"]  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_chat_stats(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):  # 定义异步函数 test_chat_stats，调用它时通常需要配合 await 使用
    """统计接口应返回向量库信息。"""

    monkeypatch.setattr(  # 使用 monkeypatch 临时替换依赖，避免测试时真的访问外部组件
        chat_router,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        "get_vectorstore_stats",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        lambda: {"total_vectors": 12, "persist_directory": "data/chroma"},  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

    response = await client.get("/chat/stats")  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
    assert response.status_code == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    data = response.json()  # 把右边计算出来的结果保存到 data 变量中，方便后面的代码继续复用
    assert data["status"] == "ok"  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert data["vector_count"] == 12  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_chat_index(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):  # 定义异步函数 test_chat_index，调用它时通常需要配合 await 使用
    """手动索引接口应能调用索引器。"""

    async def fake_index_all_news():  # 定义异步函数 fake_index_all_news，调用它时通常需要配合 await 使用
        """模拟全量索引任务，避免测试时真正访问向量库。"""
        return {"total": 1, "indexed": 1, "skipped": 0}  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    monkeypatch.setattr(indexer, "index_all_news", fake_index_all_news)  # 使用 monkeypatch 临时替换依赖，避免测试时真的访问外部组件

    response = await client.post("/chat/index")  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
    assert response.status_code == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    data = response.json()  # 把右边计算出来的结果保存到 data 变量中，方便后面的代码继续复用
    assert data["status"] == "ok"  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert data["result"]["indexed"] == 1  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
