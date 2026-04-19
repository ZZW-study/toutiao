# -*- coding: utf-8 -*-
"""Agent 服务层。

这里把"资源初始化"和"业务决策"从 node 函数里抽出来，便于：
- 惰性加载 LLM，避免 import 时就初始化。
- 在测试中直接 mock 服务。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from configs.settings import get_settings
from utils.logger import get_logger

logger = get_logger(name="AgentServices")
settings = get_settings()


@dataclass(slots=True)
class AnalysisResult:
    """封装问题分析阶段产出的结构化结果。"""
    keywords: list[str]
    category: str | None
    search_query: str


@dataclass(slots=True)
class AnswerResult:
    """封装回答生成阶段产出的结构化结果。"""
    answer: str
    is_satisfied: bool


def _extract_json_payload(content: str) -> dict[str, Any]:
    """尽量从模型输出中提取 JSON 对象。"""

    text = (content or "").strip()
    if not text:
        raise ValueError("模型输出为空")

    # 处理模型可能返回的 markdown 代码块或裸 JSON
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    elif "{" in text and "}" in text:
        text = text[text.find("{"): text.rfind("}") + 1]

    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("模型输出不是 JSON 对象")
    return data


class AnalyzeService:
    """问题分析服务。"""

    SYSTEM_PROMPT = """你是一个新闻检索分析助手。
你的任务是把用户问题拆成检索所需的关键词和新闻类别。

请严格返回 JSON：
{
  "keywords": ["关键词1", "关键词2"],
  "category": "科技/财经/国际/体育/娱乐/社会/国内/头条 或 null"
}

要求：
1. keywords 保留 2 到 5 个最有检索价值的词。
2. category 只返回给定类别之一，没有明显类别时返回 null。
3. 不要输出解释，不要输出 markdown。"""

    def __init__(self) -> None:
        """初始化分析服务，并预留模型实例占位。"""
        self._llm: Optional[ChatOpenAI] = None

    def _get_llm(self) -> ChatOpenAI:
        """按需创建分析模型。"""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY 未配置")

        # 懒初始化：第一次调用时才创建实例
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=settings.LLM_ANALYZE_MODEL,
                temperature=0.1,
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_API_BASE,
                max_retries=3,
                timeout=30,
            )
        return self._llm

    async def analyze(self, query: str, loop_count: int) -> AnalysisResult:
        """调用分析模型，生成检索需要的结构化条件。"""
        llm = self._get_llm()

        # 调用 LLM 解析用户意图
        response = await llm.ainvoke(
            [
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=query),
            ]
        )
        payload = _extract_json_payload(str(response.content))
        keywords = payload.get("keywords") or []
        if isinstance(keywords, str):
            keywords = [keywords]
        keywords = [str(item).strip() for item in keywords if str(item).strip()]
        category = payload.get("category")

        if not keywords:
            raise ValueError("模型未能提取关键词")

        # 拼接检索词，重试时追加"新闻"以扩大召回
        search_query = " ".join(keywords[:5])
        if loop_count > 0 and "新闻" not in search_query:
            search_query = f"{search_query} 新闻"

        return AnalysisResult(
            keywords=keywords[:5],
            category=category if isinstance(category, str) and category else None,
            search_query=search_query,
        )


class GenerateService:
    """回答生成服务。"""

    SYSTEM_PROMPT = """你是一个专业的新闻问答助手。
请只基于给定新闻回答用户问题，并严格返回 JSON：
{
  "answer": "回答内容",
  "is_satisfied": true
}

要求：
1. 不要编造新闻中没有的信息。
2. 如果新闻不足以回答问题，要明确说明，并返回 is_satisfied=false。
3. 不要输出 markdown，不要输出额外解释。"""

    def __init__(self) -> None:
        """初始化回答生成服务，并预留模型实例占位。"""
        self._llm: Optional[ChatOpenAI] = None

    def _get_llm(self) -> ChatOpenAI:
        """按需创建回答生成模型，避免模块导入时立即初始化。"""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY 未配置")

        # 懒初始化：生成模型温度稍高以获得更自然的回答
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=settings.LLM_GENERATE_MODEL,
                temperature=0.3,
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_API_BASE,
                max_retries=3,
                timeout=45,
            )
        return self._llm

    def build_context(self, news_list: list[dict[str, Any]], max_length: int = 2400) -> str:
        """把新闻列表压缩成模型上下文。"""

        if not news_list:
            return "没有检索到相关新闻。"

        # 逐条拼接，累计长度超过上限即截断
        parts: list[str] = []
        total_length = 0
        for index, news in enumerate(news_list, start=1):
            title = news.get("title") or "无标题"
            description = news.get("description") or (news.get("content") or "")[:180]
            snippet = f"[新闻{index}] 标题：{title}\n摘要：{description}\n"
            if total_length + len(snippet) > max_length:
                break
            parts.append(snippet)
            total_length += len(snippet)
        return "\n".join(parts)

    async def generate(
        self,
        query: str,
        news_list: list[dict[str, Any]],
        loop_count: int,
        max_loops: int,
    ) -> AnswerResult:
        """根据检索结果生成回答。"""

        llm = self._get_llm()
        context = self.build_context(news_list)
        user_prompt = f"用户问题：{query}\n\n相关新闻如下：\n{context}"

        # 调用 LLM 生成回答
        response = await llm.ainvoke(
            [
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]
        )
        payload = _extract_json_payload(str(response.content))
        answer = str(payload.get("answer") or "").strip()
        is_satisfied = bool(payload.get("is_satisfied", False))

        if not answer:
            raise ValueError("模型没有返回 answer")

        return AnswerResult(answer=answer, is_satisfied=is_satisfied)


_analyze_service: Optional[AnalyzeService] = None
_generate_service: Optional[GenerateService] = None


def get_analyze_service() -> AnalyzeService:
    """返回问题分析服务的全局单例。"""
    global _analyze_service
    if _analyze_service is None:
        _analyze_service = AnalyzeService()
    return _analyze_service


def get_generate_service() -> GenerateService:
    """返回回答生成服务的全局单例。"""
    global _generate_service
    if _generate_service is None:
        _generate_service = GenerateService()
    return _generate_service
