# 🎯 今日头条 - 新闻聚合与智能问答系统

基于 FastAPI + LLM 的新闻聚合平台，提供新闻浏览、收藏管理、智能问答等完整功能。

## ✨ 功能特性

### 📰 新闻服务
- **多源聚合**：自动从新浪、腾讯等主流新闻源抓取资讯
- **智能分类**：基于关键词规则自动分类（头条、社会、国内、国际、娱乐、体育、科技、财经）
- **定时更新**：Celery 定时任务每 6 小时自动刷新新闻
- **热度追踪**：记录新闻浏览量，支持热门新闻排序

### 💬 智能问答
- **RAG 问答系统**：基于向量检索的智能新闻问答
- **检索增强生成**：结合新闻库检索与 LLM 生成高质量回答
- **可解释性**：展示参考的新闻来源

### 👤 用户系统
- **注册/登录**：安全的用户认证系统
- **收藏管理**：收藏喜欢的新闻
- **浏览历史**：记录阅读足迹
- **个性化推荐**：基于历史行为的新闻推荐

### 🛡️ 系统特性
- **多级缓存**：本地缓存 + Redis 双重缓存
- **限流防刷**：令牌桶算法防护恶意请求
- **异步任务**：Celery 后台任务处理
- **RESTful API**：完整的 OpenAPI 文档

## 🏗️ 技术架构

```
toutiao/
├── main.py                 # FastAPI 应用入口
├── configs/                # 配置管理
│   ├── settings.py         # Pydantic Settings 配置中心
│   ├── db.py               # 数据库连接配置
│   ├── redis.py            # Redis 连接配置
│   └── celery.py           # Celery 配置
├── routers/                # API 路由
│   ├── news.py             # 新闻相关接口
│   ├── users.py            # 用户相关接口
│   ├── chat.py             # 智能问答接口
│   ├── favorite.py         # 收藏接口
│   └── history.py          # 历史记录接口
├── models/                 # SQLAlchemy 数据模型
├── schemas/                # Pydantic 请求/响应模型
├── crud/                   # 数据库操作层
├── services/               # 业务逻辑服务
├── agents/                 # LLM Agent（Graph RAG）
├── rag/                    # 检索增强生成模块
├── tasks/                  # Celery 定时任务
├── cache/                  # 多级缓存实现
├── utils/                  # 工具函数
└── middlewares/            # 中间件（限流等）
```

## 🚀 快速开始

### 环境要求

- Python 3.11+
- MySQL 8.0+
- Redis 6.0+
- RabbitMQ 3.x（用于 Celery）

### 1. 安装依赖

```bash
cd toutiao
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# 数据库配置
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB_NAME=news_app

# Redis 配置
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# RabbitMQ 配置
RABBITMQ_HOST=127.0.0.1
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# LLM 配置（用于智能问答）
OPENAI_API_KEY=your_openai_api_key
LLM_ANALYZE_MODEL=gpt-4o-mini
LLM_GENERATE_MODEL=gpt-4o-mini
```

### 3. 初始化数据库

```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS news_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 启动应用（自动创建表）
python main.py
```

### 4. 启动服务

```bash
# 开发模式（热重载）
python main.py

# 或使用 uvicorn 直接启动
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. 启动 Celery Worker（可选）

```bash
# 启动 Worker
celery -A middlewares.celery worker -l info -P eventlet

# 启动 Beat（定时任务调度器）
celery -A middlewares.celery beat -l info
```

## 📡 API 文档

服务启动后访问 `http://localhost:8000/docs` 查看完整的 OpenAPI 文档。

### 核心接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/news/categories` | 获取新闻分类列表 |
| GET | `/api/news/list?categoryId=1&page=1&pageSize=10` | 分页获取新闻 |
| GET | `/api/news/detail?id=1` | 获取新闻详情 |
| POST | `/chat` | 智能问答 |
| POST | `/api/users/register` | 用户注册 |
| POST | `/api/users/login` | 用户登录 |
| POST | `/api/favorite` | 收藏新闻 |
| GET | `/api/favorite` | 获取收藏列表 |
| GET | `/api/history` | 获取浏览历史 |

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行指定测试
pytest tests/test_news.py

# 查看覆盖率
pytest --cov=.
```

## 📦 项目结构说明

```
toutiao/
├── main.py                 # 应用入口，负责初始化和生命周期管理
├── configs/                # 配置模块
│   ├── settings.py         # 主配置类，Pydantic Settings
│   ├── db.py               # SQLAlchemy 异步数据库连接
│   ├── redis.py            # Redis 连接池配置
│   └── celery.py           # Celery 应用配置
├── routers/                # FastAPI 路由
│   ├── news.py             # 新闻 CRUD 接口
│   ├── users.py            # 用户认证接口
│   ├── chat.py             # RAG 问答接口
│   ├── favorite.py         # 收藏管理
│   └── history.py          # 历史记录
├── models/                 # SQLAlchemy ORM 模型
├── schemas/                # Pydantic 数据模型
├── crud/                   # 数据库操作封装
├── services/               # 业务逻辑服务类
├── agents/                 # LLM Agent 实现
│   ├── graph.py            # Agent 执行图
│   ├── nodes/              # Agent 节点
│   │   ├── analyze.py      # 问题分析节点
│   │   ├── retrieve.py     # 检索节点
│   │   └── generate.py     # 回答生成节点
│   └── services/           # Agent 服务
├── rag/                    # 检索增强生成
│   ├── embeddings.py       # 向量化服务
│   └── vectorstore.py      # 向量存储
├── tasks/                  # Celery 异步任务
│   ├── news_spider_tasks.py # 新闻爬取任务
│   ├── news_tasks.py       # 新闻热度统计
│   └── statistics_tasks.py # 用户行为统计
├── cache/                  # 缓存层
│   ├── multi_level_cache.py # 多级缓存实现
│   ├── local_cache.py      # 本地 LRU 缓存
│   └── redis_cache.py      # Redis 分布式缓存
├── utils/                  # 工具函数
├── middlewares/            # 中间件
│   ├── rate_limit.py       # 限流中间件
│   └── token_bucket_middleware.py # 令牌桶限流
└── tests/                  # 测试用例
```

## 🔧 配置说明

### 新闻源配置

在 `configs/settings.py` 的 `SPIDER_NEWS_SOURCES` 属性中配置：

```python
{
    "name": "sina",
    "url": "https://feed.mix.sina.com.cn/api/roll/get?...",
    "type": "json",  # 或 "rss"
    "enabled": True,
}
```

### 分类规则配置

在 `configs/settings.py` 的 `SPIDER_CLASSIFICATION_RULES` 属性中配置关键词规则。

### 限流配置

```bash
RATE_LIMIT_PER_SECOND=3      # 每秒请求限制
RATE_LIMIT_PER_MINUTE=100    # 每分钟请求限制
TOKEN_BUCKET_CAPACITY=10     # 令牌桶容量
IP_RATE_LIMIT=60             # 单 IP 每分钟限制
```

## 🐳 Docker 部署

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 📝 技术亮点

1. **异步架构**：使用 asyncio + aiomysql 实现高并发
2. **多级缓存**：本地内存 + Redis 双重缓存策略
3. **RAG 问答**：基于 LangGraph 的智能问答 Agent
4. **限流防护**：令牌桶算法防止恶意请求
5. **Celery 异步**：定时任务与异步任务分离

## 📄 许可证

MIT License

## One-Command Dev Startup

项目现在支持在仓库根目录一条命令同时启动后端和前端开发服务。

### 首次准备

先安装根目录开发编排依赖：

```bash
npm install
```

再安装前端依赖：

```bash
npm run setup:client
```

如果你已经在 `client/` 目录执行过 `npm install`，这一步可以跳过。

### 日常开发启动

在仓库根目录执行：

```bash
npm run dev
```

这个命令会同时启动：

- 后端：`python main.py`
- 前端：`npm --prefix client run dev`

默认访问地址：

- 前端：`http://localhost:5173`
- 后端：`http://127.0.0.1:8000`
- 后端文档：`http://127.0.0.1:8000/docs`

### 单独启动某一端

只启动后端：

```bash
npm run dev:server
```

只启动前端：

```bash
npm run dev:client
```
