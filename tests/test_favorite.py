# -*- coding: utf-8 -*-
"""
收藏接口测试
"""
import pytest  # 导入 pytest 模块，给当前文件后面的逻辑使用
from httpx import AsyncClient  # 从 httpx 模块导入当前文件后续要用到的对象


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_check_favorite_success(client: AsyncClient, auth_headers):  # 定义异步函数 test_check_favorite_success，调用它时通常需要配合 await 使用
    """测试检查收藏状态（成功）"""
    response = await client.get(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/favorite/check",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        params={"newsId": 1},  # 把右边计算出来的结果保存到 params 变量中，方便后面的代码继续复用
        headers=auth_headers  # 把右边计算出来的结果保存到 headers 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    data = response.json()  # 把右边计算出来的结果保存到 data 变量中，方便后面的代码继续复用
    assert data["code"] == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert "data" in data  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert "isFavorite" in data["data"]  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_check_favorite_unauthorized(client: AsyncClient):  # 定义异步函数 test_check_favorite_unauthorized，调用它时通常需要配合 await 使用
    """测试检查收藏状态（未授权）"""
    response = await client.get(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/favorite/check",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        params={"newsId": 1}  # 把右边计算出来的结果保存到 params 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 401  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_add_favorite_success(client: AsyncClient, auth_headers):  # 定义异步函数 test_add_favorite_success，调用它时通常需要配合 await 使用
    """测试添加收藏（成功）"""
    response = await client.post(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/favorite/add",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        headers=auth_headers,  # 把右边计算出来的结果保存到 headers 变量中，方便后面的代码继续复用
        json={"newsId": 1}  # 把右边计算出来的结果保存到 json 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    data = response.json()  # 把右边计算出来的结果保存到 data 变量中，方便后面的代码继续复用
    assert data["code"] == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_add_favorite_duplicate(client: AsyncClient, auth_headers):  # 定义异步函数 test_add_favorite_duplicate，调用它时通常需要配合 await 使用
    """测试添加收藏（重复收藏）"""
    await client.post(  # 等待这个异步操作完成，再继续执行后面的代码
        "/api/favorite/add",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        headers=auth_headers,  # 把右边计算出来的结果保存到 headers 变量中，方便后面的代码继续复用
        json={"newsId": 2}  # 把右边计算出来的结果保存到 json 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    response = await client.post(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/favorite/add",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        headers=auth_headers,  # 把右边计算出来的结果保存到 headers 变量中，方便后面的代码继续复用
        json={"newsId": 2}  # 把右边计算出来的结果保存到 json 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code in [200, 400, 500]  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_remove_favorite_success(client: AsyncClient, auth_headers):  # 定义异步函数 test_remove_favorite_success，调用它时通常需要配合 await 使用
    """测试取消收藏（成功）"""
    await client.post(  # 等待这个异步操作完成，再继续执行后面的代码
        "/api/favorite/add",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        headers=auth_headers,  # 把右边计算出来的结果保存到 headers 变量中，方便后面的代码继续复用
        json={"newsId": 3}  # 把右边计算出来的结果保存到 json 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    response = await client.delete(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/favorite/remove",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        params={"newsId": 3},  # 把右边计算出来的结果保存到 params 变量中，方便后面的代码继续复用
        headers=auth_headers  # 把右边计算出来的结果保存到 headers 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    data = response.json()  # 把右边计算出来的结果保存到 data 变量中，方便后面的代码继续复用
    assert data["code"] == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_remove_favorite_not_found(client: AsyncClient, auth_headers):  # 定义异步函数 test_remove_favorite_not_found，调用它时通常需要配合 await 使用
    """测试取消收藏（记录不存在）"""
    response = await client.delete(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/favorite/remove",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        params={"newsId": 99999},  # 把右边计算出来的结果保存到 params 变量中，方便后面的代码继续复用
        headers=auth_headers  # 把右边计算出来的结果保存到 headers 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code in [200, 404]  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_get_favorite_list_success(client: AsyncClient, auth_headers):  # 定义异步函数 test_get_favorite_list_success，调用它时通常需要配合 await 使用
    """测试获取收藏列表（成功）"""
    response = await client.get(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/favorite/list",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        params={"page": 1, "pageSize": 10},  # 把右边计算出来的结果保存到 params 变量中，方便后面的代码继续复用
        headers=auth_headers  # 把右边计算出来的结果保存到 headers 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    data = response.json()  # 把右边计算出来的结果保存到 data 变量中，方便后面的代码继续复用
    assert data["code"] == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert "data" in data  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert "list" in data["data"]  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert "total" in data["data"]  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_get_favorite_list_pagination(client: AsyncClient, auth_headers):  # 定义异步函数 test_get_favorite_list_pagination，调用它时通常需要配合 await 使用
    """测试获取收藏列表（分页）"""
    response = await client.get(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/favorite/list",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        params={"page": 1, "pageSize": 5},  # 把右边计算出来的结果保存到 params 变量中，方便后面的代码继续复用
        headers=auth_headers  # 把右边计算出来的结果保存到 headers 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_clear_favorites_success(client: AsyncClient, auth_headers):  # 定义异步函数 test_clear_favorites_success，调用它时通常需要配合 await 使用
    """测试清空收藏（成功）"""
    response = await client.delete(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/favorite/clear",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        headers=auth_headers  # 把右边计算出来的结果保存到 headers 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    data = response.json()  # 把右边计算出来的结果保存到 data 变量中，方便后面的代码继续复用
    assert data["code"] == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
