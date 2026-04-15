# -*- coding: utf-8 -*-
"""
新闻接口测试
"""
import pytest  # 导入 pytest 模块，给当前文件后面的逻辑使用
from httpx import AsyncClient  # 从 httpx 模块导入当前文件后续要用到的对象


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_get_news_categories(client: AsyncClient):  # 定义异步函数 test_get_news_categories，调用它时通常需要配合 await 使用
    """测试获取新闻分类"""
    response = await client.get("/api/news/categories")  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
    assert response.status_code == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    data = response.json()  # 把右边计算出来的结果保存到 data 变量中，方便后面的代码继续复用
    assert data["code"] == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert "data" in data  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert isinstance(data["data"], list)  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_get_news_categories_with_pagination(client: AsyncClient):  # 定义异步函数 test_get_news_categories_with_pagination，调用它时通常需要配合 await 使用
    """测试获取新闻分类（带分页参数）"""
    response = await client.get("/api/news/categories", params={"skip": 0, "limit": 10})  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
    assert response.status_code == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    data = response.json()  # 把右边计算出来的结果保存到 data 变量中，方便后面的代码继续复用
    assert data["code"] == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_get_news_list_success(client: AsyncClient):  # 定义异步函数 test_get_news_list_success，调用它时通常需要配合 await 使用
    """测试获取新闻列表（成功）"""
    response = await client.get(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/news/list",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        params={"categoryId": 1, "page": 1, "pageSize": 10}  # 把右边计算出来的结果保存到 params 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    data = response.json()  # 把右边计算出来的结果保存到 data 变量中，方便后面的代码继续复用
    assert data["code"] == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert "data" in data  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert "list" in data["data"]  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert "total" in data["data"]  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert "hasMore" in data["data"]  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_get_news_list_invalid_category(client: AsyncClient):  # 定义异步函数 test_get_news_list_invalid_category，调用它时通常需要配合 await 使用
    """测试获取新闻列表（无效分类）"""
    response = await client.get(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/news/list",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        params={"categoryId": -1, "page": 1, "pageSize": 10}  # 把右边计算出来的结果保存到 params 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 422  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_get_news_list_invalid_page(client: AsyncClient):  # 定义异步函数 test_get_news_list_invalid_page，调用它时通常需要配合 await 使用
    """测试获取新闻列表（无效页码）"""
    response = await client.get(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/news/list",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        params={"categoryId": 1, "page": 0, "pageSize": 10}  # 把右边计算出来的结果保存到 params 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 422  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_get_news_list_page_size_limit(client: AsyncClient):  # 定义异步函数 test_get_news_list_page_size_limit，调用它时通常需要配合 await 使用
    """测试获取新闻列表（页大小超限）"""
    response = await client.get(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/news/list",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        params={"categoryId": 1, "page": 1, "pageSize": 200}  # 把右边计算出来的结果保存到 params 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 422  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_get_news_detail_success(client: AsyncClient):  # 定义异步函数 test_get_news_detail_success，调用它时通常需要配合 await 使用
    """测试获取新闻详情（成功）"""
    response = await client.get(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/news/detail",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        params={"id": 1}  # 把右边计算出来的结果保存到 params 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    if response.status_code == 200:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        data = response.json()  # 把右边计算出来的结果保存到 data 变量中，方便后面的代码继续复用
        assert data["code"] == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
        assert "data" in data  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
        assert "id" in data["data"]  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
        assert "title" in data["data"]  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    elif response.status_code == 404:  # 当前面的条件不满足时，再继续判断这一条备用条件
        assert "message" in response.json()  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_get_news_detail_not_found(client: AsyncClient):  # 定义异步函数 test_get_news_detail_not_found，调用它时通常需要配合 await 使用
    """测试获取新闻详情（不存在）"""
    response = await client.get(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/news/detail",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        params={"id": 99999}  # 把右边计算出来的结果保存到 params 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code in [404, 500]  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_get_news_detail_missing_id(client: AsyncClient):  # 定义异步函数 test_get_news_detail_missing_id，调用它时通常需要配合 await 使用
    """测试获取新闻详情（缺少ID）"""
    response = await client.get("/api/news/detail")  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
    assert response.status_code == 422  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
