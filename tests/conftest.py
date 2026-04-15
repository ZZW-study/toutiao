# -*- coding: utf-8 -*-
"""
pytest fixtures for toutiao_backend
"""
import pytest  # 导入 pytest 模块，给当前文件后面的逻辑使用
import asyncio  # 导入 asyncio 模块，给当前文件后面的逻辑使用
from typing import Generator, AsyncGenerator  # 从 typing 模块导入当前文件后续要用到的对象
from httpx import AsyncClient, ASGITransport  # 从 httpx 模块导入当前文件后续要用到的对象
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker  # 从 sqlalchemy.ext.asyncio 模块导入当前文件后续要用到的对象
from sqlalchemy.pool import StaticPool  # 从 sqlalchemy.pool 模块导入当前文件后续要用到的对象

from main import app  # 从 main 模块导入当前文件后续要用到的对象
from configs.db import get_db  # 从 configs.db 模块导入当前文件后续要用到的对象
from models.users import User  # 从 models.users 模块导入当前文件后续要用到的对象
from models.news import Category, News  # 从 models.news 模块导入当前文件后续要用到的对象
from utils import security  # 从 utils 模块导入当前文件后续要用到的对象


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"  # 把这个常量值保存到 TEST_DATABASE_URL 中，后面会作为固定配置反复使用


@pytest.fixture(scope="session")  # 使用 pytest.fixture 装饰下面的函数或类，给它附加额外能力
def event_loop() -> Generator:  # 定义函数 event_loop，把一段可以复用的逻辑单独封装起来
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()  # 把右边计算出来的结果保存到 loop 变量中，方便后面的代码继续复用
    yield loop  # 把当前值先交给外层使用，同时保留生成器现场，后面还能继续执行
    loop.close()  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行


@pytest.fixture(scope="function")  # 使用 pytest.fixture 装饰下面的函数或类，给它附加额外能力
async def test_db() -> AsyncGenerator[AsyncSession, None]:  # 定义异步函数 test_db，调用它时通常需要配合 await 使用
    """创建测试数据库会话。

    这里显式使用 `StaticPool`，原因是 SQLite 的内存数据库默认“每个连接一份数据”。
    如果不固定连接池，`create_all` 建的表和测试请求实际使用的连接可能不是同一个，
    结果就是表看起来创建了，但请求一跑仍然提示“no such table”。
    """
    engine = create_async_engine(  # 把右边计算出来的结果保存到 engine 变量中，方便后面的代码继续复用
        TEST_DATABASE_URL,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        echo=False,  # 把右边计算出来的结果保存到 echo 变量中，方便后面的代码继续复用
        connect_args={"check_same_thread": False},  # 把右边计算出来的结果保存到 connect_args 变量中，方便后面的代码继续复用
        poolclass=StaticPool,  # 把右边计算出来的结果保存到 poolclass 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    async_session = async_sessionmaker(engine, expire_on_commit=False)  # 把右边计算出来的结果保存到 async_session 变量中，方便后面的代码继续复用

    async with async_session() as session:  # 以异步上下文管理的方式使用资源，结束时会自动做清理
        from models.users import Base as UserBase  # 从 models.users 模块导入当前文件后续要用到的对象
        from models.news import Base as NewsBase  # 从 models.news 模块导入当前文件后续要用到的对象
        from models.favorite import Base as FavoriteBase  # 从 models.favorite 模块导入当前文件后续要用到的对象
        from models.history import Base as HistoryBase  # 从 models.history 模块导入当前文件后续要用到的对象

        async with engine.begin() as conn:  # 以异步上下文管理的方式使用资源，结束时会自动做清理
            await conn.run_sync(UserBase.metadata.create_all)  # 等待这个异步操作完成，再继续执行后面的代码
            await conn.run_sync(NewsBase.metadata.create_all)  # 等待这个异步操作完成，再继续执行后面的代码
            await conn.run_sync(FavoriteBase.metadata.create_all)  # 等待这个异步操作完成，再继续执行后面的代码
            await conn.run_sync(HistoryBase.metadata.create_all)  # 等待这个异步操作完成，再继续执行后面的代码

        # 预置基础分类和一条新闻，保证新闻详情、收藏、历史等接口在测试中有稳定数据。
        categories = [  # 把右边计算出来的结果保存到 categories 变量中，方便后面的代码继续复用
            Category(id=1, name="头条", sort_order=1),  # 把右边计算出来的结果保存到 Category(id 变量中，方便后面的代码继续复用
            Category(id=7, name="科技", sort_order=7),  # 把右边计算出来的结果保存到 Category(id 变量中，方便后面的代码继续复用
        ]  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
        session.add_all(categories)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        await session.flush()  # 等待这个异步操作完成，再继续执行后面的代码

        session.add(  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            News(  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                id=1,  # 把右边计算出来的结果保存到 id 变量中，方便后面的代码继续复用
                title="测试新闻",  # 把右边计算出来的结果保存到 title 变量中，方便后面的代码继续复用
                description="用于自动化测试的新闻摘要",  # 把右边计算出来的结果保存到 description 变量中，方便后面的代码继续复用
                content="用于自动化测试的新闻正文内容",  # 把右边计算出来的结果保存到 content 变量中，方便后面的代码继续复用
                image=None,  # 把右边计算出来的结果保存到 image 变量中，方便后面的代码继续复用
                author="测试作者",  # 把右边计算出来的结果保存到 author 变量中，方便后面的代码继续复用
                category_id=1,  # 把右边计算出来的结果保存到 category_id 变量中，方便后面的代码继续复用
                views=0,  # 把右边计算出来的结果保存到 views 变量中，方便后面的代码继续复用
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
        )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
        await session.commit()  # 等待这个异步操作完成，再继续执行后面的代码

        yield session  # 把当前值先交给外层使用，同时保留生成器现场，后面还能继续执行

        async with engine.begin() as conn:  # 以异步上下文管理的方式使用资源，结束时会自动做清理
            await conn.run_sync(UserBase.metadata.drop_all)  # 等待这个异步操作完成，再继续执行后面的代码
            await conn.run_sync(NewsBase.metadata.drop_all)  # 等待这个异步操作完成，再继续执行后面的代码
            await conn.run_sync(FavoriteBase.metadata.drop_all)  # 等待这个异步操作完成，再继续执行后面的代码
            await conn.run_sync(HistoryBase.metadata.drop_all)  # 等待这个异步操作完成，再继续执行后面的代码

    await engine.dispose()  # 等待这个异步操作完成，再继续执行后面的代码


@pytest.fixture(scope="function")  # 使用 pytest.fixture 装饰下面的函数或类，给它附加额外能力
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:  # 定义异步函数 client，调用它时通常需要配合 await 使用
    """创建绑定测试数据库的 HTTP 客户端。"""
    async def override_get_db():  # 定义异步函数 override_get_db，调用它时通常需要配合 await 使用
        """测试时把正式数据库依赖替换成内存数据库会话。"""
        yield test_db  # 把当前值先交给外层使用，同时保留生成器现场，后面还能继续执行

    app.dependency_overrides[get_db] = override_get_db  # 继续调用应用对象的方法，完成注册、配置或挂载等动作

    transport = ASGITransport(app=app)  # 把右边计算出来的结果保存到 transport 变量中，方便后面的代码继续复用
    async with AsyncClient(transport=transport, base_url="http://test") as ac:  # 以异步上下文管理的方式使用资源，结束时会自动做清理
        yield ac  # 把当前值先交给外层使用，同时保留生成器现场，后面还能继续执行

    app.dependency_overrides.clear()  # 继续调用应用对象的方法，完成注册、配置或挂载等动作


@pytest.fixture(scope="function")  # 使用 pytest.fixture 装饰下面的函数或类，给它附加额外能力
async def test_user(test_db: AsyncSession) -> User:  # 定义异步函数 test_user，调用它时通常需要配合 await 使用
    """Create test user"""
    user = User(  # 把右边计算出来的结果保存到 user 变量中，方便后面的代码继续复用
        username="testuser",  # 把右边计算出来的结果保存到 username 变量中，方便后面的代码继续复用
        password=security.get_hash_password("testpass123")  # 把右边计算出来的结果保存到 password 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    test_db.add(user)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    await test_db.commit()  # 等待这个异步操作完成，再继续执行后面的代码
    await test_db.refresh(user)  # 等待这个异步操作完成，再继续执行后面的代码
    return user  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


@pytest.fixture(scope="function")  # 使用 pytest.fixture 装饰下面的函数或类，给它附加额外能力
async def auth_headers(client: AsyncClient, test_user: User) -> dict:  # 定义异步函数 auth_headers，调用它时通常需要配合 await 使用
    """Get authentication headers for test user"""
    response = await client.post(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/user/login",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        json={"username": "testuser", "password": "testpass123"}  # 把右边计算出来的结果保存到 json 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    data = response.json()  # 把右边计算出来的结果保存到 data 变量中，方便后面的代码继续复用
    token = data.get("data", {}).get("token")  # 把右边计算出来的结果保存到 token 变量中，方便后面的代码继续复用
    return {"Authorization": f"Bearer {token}"}  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
