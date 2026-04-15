# -*- coding: utf-8 -*-
"""
pytest fixtures for toutiao_backend
"""
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from configs.db_conf import get_db
from models.users import User
from models.news import Category, News
from utils import security


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话。

    这里显式使用 `StaticPool`，原因是 SQLite 的内存数据库默认“每个连接一份数据”。
    如果不固定连接池，`create_all` 建的表和测试请求实际使用的连接可能不是同一个，
    结果就是表看起来创建了，但请求一跑仍然提示“no such table”。
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        from models.users import Base as UserBase
        from models.news import Base as NewsBase
        from models.favorite import Base as FavoriteBase
        from models.history import Base as HistoryBase

        async with engine.begin() as conn:
            await conn.run_sync(UserBase.metadata.create_all)
            await conn.run_sync(NewsBase.metadata.create_all)
            await conn.run_sync(FavoriteBase.metadata.create_all)
            await conn.run_sync(HistoryBase.metadata.create_all)

        # 预置基础分类和一条新闻，保证新闻详情、收藏、历史等接口在测试中有稳定数据。
        categories = [
            Category(id=1, name="头条", sort_order=1),
            Category(id=7, name="科技", sort_order=7),
        ]
        session.add_all(categories)
        await session.flush()

        session.add(
            News(
                id=1,
                title="测试新闻",
                description="用于自动化测试的新闻摘要",
                content="用于自动化测试的新闻正文内容",
                image=None,
                author="测试作者",
                category_id=1,
                views=0,
            )
        )
        await session.commit()

        yield session

        async with engine.begin() as conn:
            await conn.run_sync(UserBase.metadata.drop_all)
            await conn.run_sync(NewsBase.metadata.drop_all)
            await conn.run_sync(FavoriteBase.metadata.drop_all)
            await conn.run_sync(HistoryBase.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """创建绑定测试数据库的 HTTP 客户端。"""
    async def override_get_db():
        """测试时把正式数据库依赖替换成内存数据库会话。"""
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def test_user(test_db: AsyncSession) -> User:
    """Create test user"""
    user = User(
        username="testuser",
        password=security.get_hash_password("testpass123")
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
async def auth_headers(client: AsyncClient, test_user: User) -> dict:
    """Get authentication headers for test user"""
    response = await client.post(
        "/api/user/login",
        json={"username": "testuser", "password": "testpass123"}
    )
    assert response.status_code == 200
    data = response.json()
    token = data.get("data", {}).get("token")
    return {"Authorization": f"Bearer {token}"}
