# 新闻问答 Agent 设计方案

## 一、功能描述

用户用自然语言提问新闻相关内容，Agent 检索新闻库并给出回答。

**示例问题：**
- "华为最近有什么动作？"
- "最近股市行情怎么样？"
- "有什么国际大事件？"

---

## 二、架构设计

```
用户提问
    │
    ▼
┌─────────────────────────────────────────────────┐
│              LangGraph 编排                      │
│                                                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│   │ 问题分析  │───▶│ 新闻检索  │───▶│ 回答生成  │ │
│   │  Agent   │    │  Agent   │    │  Agent   │ │
│   └──────────┘    └──────────┘    └──────────┘ │
│         ▲                               │       │
│         └───────────────────────────────┘       │
│              (循环判断：回答不满意则重试)          │
└─────────────────────────────────────────────────┘
    │
    ▼
回答用户
```

---

## 三、Agent 编排流程

```python
# LangGraph 流程

1. 问题分析Agent
   - 提取关键词
   - 识别类别（科技/财经/国际等）
   - 生成检索query

2. 新闻检索Agent
   - 向量检索相似新闻
   - 数据库补充查询
   - 返回相关新闻列表

3. 回答生成Agent
   - 基于检索结果生成回答
   - 判断回答是否充分

4. 循环判断
   - 如果回答不充分 → 返回问题分析Agent，调整query重试
   - 如果回答充分 → 输出最终答案

最多循环3次
```

---

## 四、目录结构

```
toutiao_bankend/
├── agents/                     # 新增：独立模块
│   ├── __init__.py
│   ├── graph.py               # LangGraph 编排入口
│   ├── state.py               # 状态定义
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── analyze.py         # 问题分析节点
│   │   ├── retrieve.py        # 新闻检索节点
│   │   └── generate.py        # 回答生成节点
│   └── tools/
│       ├── __init__.py
│       └── news_retriever.py  # 新闻检索工具
├── rag/                       # 新增：RAG模块
│   ├── __init__.py
│   ├── embeddings.py          # Embedding模型
│   ├── vectorstore.py         # 向量存储
│   └── indexer.py             # 新闻索引构建
├── routers/
│   └── chat.py                # 新增：API接口
└── data/
    └── chroma/                # 向量数据库存储
```

---

## 五、依赖安装

```txt
# requirements.txt 新增
langgraph>=0.2.0
langchain>=0.3.0
langchain-openai>=0.2.0
langchain-community>=0.3.0
chromadb>=0.4.0
sentence-transformers>=2.2.0
```

---

## 六、核心代码

### 6.1 状态定义 (agents/state.py)

```python
from typing import TypedDict

class AgentState(TypedDict):
    """Agent状态"""
    query: str                    # 用户原始问题
    keywords: list[str]           # 提取的关键词
    category: str | None          # 识别的类别
    search_query: str             # 检索用的query
    news_list: list[dict]         # 检索到的新闻
    answer: str                   # 生成的回答
    loop_count: int               # 循环次数
    is_satisfied: bool            # 回答是否充分
```

### 6.2 LangGraph 编排 (agents/graph.py)

```python
from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.nodes.analyze import analyze_node
from agents.nodes.retrieve import retrieve_node
from agents.nodes.generate import generate_node

def should_continue(state: AgentState) -> str:
    """判断是否继续循环"""
    if state["is_satisfied"]:
        return "end"
    if state["loop_count"] >= 3:
        return "end"
    return "retry"

# 构建图
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("analyze", analyze_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("generate", generate_node)

# 设置入口
workflow.set_entry_point("analyze")

# 添加边
workflow.add_edge("analyze", "retrieve")
workflow.add_edge("retrieve", "generate")

# 循环判断
workflow.add_conditional_edges(
    "generate",
    should_continue,
    {
        "end": END,
        "retry": "analyze"
    }
)

# 编译
app = workflow.compile()
```

### 6.3 问题分析节点 (agents/nodes/analyze.py)

```python
from langchain_openai import ChatOpenAI
from agents.state import AgentState

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

async def analyze_node(state: AgentState) -> dict:
    """问题分析节点"""
    query = state["query"]
    loop_count = state.get("loop_count", 0)

    prompt = f"""
    分析以下用户问题，提取：
    1. 关键词（用于检索）
    2. 新闻类别（科技/财经/国际/体育/娱乐/社会/国内/头条，不确定则为null）

    用户问题：{query}

    以JSON格式返回：{{"keywords": [...], "category": "..."}}
    """

    response = await llm.ainvoke(prompt)
    import json
    result = json.loads(response.content)

    # 如果是重试，扩展关键词
    search_query = " ".join(result["keywords"])
    if loop_count > 0:
        search_query = f"{search_query} 相关新闻"

    return {
        "keywords": result["keywords"],
        "category": result.get("category"),
        "search_query": search_query,
        "loop_count": loop_count + 1
    }
```

### 6.4 新闻检索节点 (agents/nodes/retrieve.py)

```python
from agents.state import AgentState
from agents.tools.news_retriever import search_news

async def retrieve_node(state: AgentState) -> dict:
    """新闻检索节点"""
    search_query = state["search_query"]
    category = state.get("category")

    # 从向量库和数据库检索
    news_list = await search_news(search_query, category, top_k=5)

    return {"news_list": news_list}
```

### 6.5 回答生成节点 (agents/nodes/generate.py)

```python
from langchain_openai import ChatOpenAI
from agents.state import AgentState

llm = ChatOpenAI(model="gpt-4o-mini")

async def generate_node(state: AgentState) -> dict:
    """回答生成节点"""
    query = state["query"]
    news_list = state["news_list"]

    if not news_list:
        return {
            "answer": "抱歉，没有找到相关新闻。",
            "is_satisfied": False
        }

    # 构建上下文
    context = "\n".join([
        f"- {n['title']}：{n['content'][:200]}..."
        for n in news_list
    ])

    prompt = f"""
    基于以下新闻回答用户问题，并判断回答是否充分。

    用户问题：{query}

    相关新闻：
    {context}

    请回答问题，并以JSON格式返回：
    {{"answer": "你的回答", "is_satisfied": true/false}}
    """

    response = await llm.ainvoke(prompt)
    import json
    result = json.loads(response.content)

    return {
        "answer": result["answer"],
        "is_satisfied": result.get("is_satisfied", True)
    }
```

### 6.6 新闻检索工具 (agents/tools/news_retriever.py)

```python
from rag.vectorstore import get_vectorstore
from configs.db_conf import AsyncSessionLocal
from sqlalchemy import select, text
from models.news import News

async def search_news(query: str, category: str | None, top_k: int = 5) -> list[dict]:
    """检索新闻"""
    results = []

    # 1. 向量检索
    vectorstore = get_vectorstore()
    docs = vectorstore.similarity_search(query, k=top_k * 2)

    # 2. 数据库补充
    async with AsyncSessionLocal() as db:
        for doc in docs:
            news_id = doc.metadata.get("news_id")
            if news_id:
                stmt = select(News).where(News.id == news_id)
                result = await db.execute(stmt)
                news = result.scalar_one_or_none()
                if news:
                    results.append({
                        "id": news.id,
                        "title": news.title,
                        "content": news.content,
                        "category_id": news.category_id
                    })

    # 3. 如果有类别过滤
    if category:
        category_map = {
            "头条": 1, "社会": 2, "国内": 3, "国际": 4,
            "娱乐": 5, "体育": 6, "科技": 7, "财经": 8
        }
        cat_id = category_map.get(category)
        if cat_id:
            results = [r for r in results if r["category_id"] == cat_id]

    return results[:top_k]
```

### 6.7 API 接口 (routers/chat.py)

```python
from fastapi import APIRouter
from pydantic import BaseModel
from agents.graph import app as agent_app

router = APIRouter(prefix="/chat", tags=["新闻问答"])

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str
    news_list: list[dict]

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """新闻问答接口"""
    result = await agent_app.ainvoke({"query": request.query})

    return ChatResponse(
        answer=result["answer"],
        news_list=result.get("news_list", [])
    )
```

---

## 七、使用流程

```
1. 首先运行索引脚本，将新闻导入向量库
   python -m rag.indexer

2. 启动服务
   python main.py

3. 调用接口
   POST /chat/
   {"query": "华为最近有什么新闻？"}

4. 返回结果
   {
     "answer": "华为最近发布了...",
     "news_list": [...]
   }
```

---

## 八、配置 (.env 新增)

```env
# LLM
OPENAI_API_KEY=your_key
OPENAI_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# RAG
CHROMA_PERSIST_DIR=./data/chroma
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

---

## 九、关键特点

| 特点 | 说明 |
|-----|------|
| 独立模块 | agents/ 和 rag/ 目录，不改动现有代码 |
| LangGraph编排 | 3个Agent节点，有循环逻辑 |
| 循环重试 | 回答不满意时重新分析检索，最多3次 |
| RAG检索 | 向量库 + 数据库双重检索 |
| 简单易扩展 | 可随时增加新节点或工具 |
