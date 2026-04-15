# -*- coding: utf-8 -*-
"""Agent 服务层。

这里把“资源初始化”和“业务决策”从 node 函数里抽出来，便于：
- 惰性加载 LLM，避免 import 时就初始化。
- 在测试中直接 mock 服务。
- 在没有 LLM 凭证时提供可控的规则兜底。
"""

from __future__ import annotations  # 开启延迟解析类型注解，避免前向引用在导入阶段就被过早求值

import json  # 导入 json 模块，给当前文件后面的逻辑使用
import re  # 导入 re 模块，给当前文件后面的逻辑使用
from dataclasses import dataclass  # 从 dataclasses 模块导入当前文件后续要用到的对象
from typing import Any, Optional  # 从 typing 模块导入当前文件后续要用到的对象

from langchain_core.messages import HumanMessage, SystemMessage  # 从 langchain_core.messages 模块导入当前文件后续要用到的对象
from langchain_openai import ChatOpenAI  # 从 langchain_openai 模块导入当前文件后续要用到的对象

from configs.settings import get_settings  # 从 configs.settings 模块导入当前文件后续要用到的对象
from utils.logger import get_logger  # 从 utils.logger 模块导入当前文件后续要用到的对象

logger = get_logger(name="AgentServices")  # 把右边计算出来的结果保存到 logger 变量中，方便后面的代码继续复用
settings = get_settings()  # 把右边计算出来的结果保存到 settings 变量中，方便后面的代码继续复用


@dataclass(slots=True)  # 使用 dataclass 装饰下面的函数或类，给它附加额外能力
class AnalysisResult:  # 定义 AnalysisResult 类，用来把这一块相关的状态和行为组织在一起
    """封装问题分析阶段产出的结构化结果。"""
    keywords: list[str]  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    category: str | None  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    search_query: str  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行


@dataclass(slots=True)  # 使用 dataclass 装饰下面的函数或类，给它附加额外能力
class AnswerResult:  # 定义 AnswerResult 类，用来把这一块相关的状态和行为组织在一起
    """封装回答生成阶段产出的结构化结果。"""
    answer: str  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    is_satisfied: bool  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行


def _extract_json_payload(content: str) -> dict[str, Any]:  # 定义函数 _extract_json_payload，把一段可以复用的逻辑单独封装起来
    """尽量从模型输出中提取 JSON 对象。"""

    text = (content or "").strip()  # 把右边计算出来的结果保存到 text 变量中，方便后面的代码继续复用
    if not text:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        raise ValueError("模型输出为空")  # 主动抛出异常，让上层知道这里出现了需要处理的问题

    if "```json" in text:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()  # 把右边计算出来的结果保存到 text 变量中，方便后面的代码继续复用
    elif "```" in text:  # 当前面的条件不满足时，再继续判断这一条备用条件
        text = text.split("```", 1)[1].split("```", 1)[0].strip()  # 把右边计算出来的结果保存到 text 变量中，方便后面的代码继续复用
    elif "{" in text and "}" in text:  # 当前面的条件不满足时，再继续判断这一条备用条件
        text = text[text.find("{"): text.rfind("}") + 1]  # 把右边计算出来的结果保存到 text 变量中，方便后面的代码继续复用

    data = json.loads(text)  # 把右边计算出来的结果保存到 data 变量中，方便后面的代码继续复用
    if not isinstance(data, dict):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        raise ValueError("模型输出不是 JSON 对象")  # 主动抛出异常，让上层知道这里出现了需要处理的问题
    return data  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


class AnalyzeService:  # 定义 AnalyzeService 类，用来把这一块相关的状态和行为组织在一起
    """问题分析服务。"""

    # 这里开始定义一个多行提示词字符串，后面几行都会作为模型提示内容的一部分
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

    def __init__(self) -> None:  # 定义函数 __init__，把一段可以复用的逻辑单独封装起来
        """初始化分析服务，并预留模型实例占位。"""
        self._llm: Optional[ChatOpenAI] = None  # 把右边计算出来的结果保存到 _llm 变量中，方便后面的代码继续复用

    def _get_llm(self) -> Optional[ChatOpenAI]:  # 定义函数 _get_llm，把一段可以复用的逻辑单独封装起来
        """按需创建分析模型。"""

        if not settings.OPENAI_API_KEY:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return None  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        if self._llm is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            self._llm = ChatOpenAI(  # 把右边计算出来的结果保存到 _llm 变量中，方便后面的代码继续复用
                model=settings.LLM_ANALYZE_MODEL,  # 把右边计算出来的结果保存到 model 变量中，方便后面的代码继续复用
                temperature=0.1,  # 把右边计算出来的结果保存到 temperature 变量中，方便后面的代码继续复用
                openai_api_key=settings.OPENAI_API_KEY,  # 把右边计算出来的结果保存到 openai_api_key 变量中，方便后面的代码继续复用
                openai_api_base=settings.OPENAI_API_BASE,  # 把右边计算出来的结果保存到 openai_api_base 变量中，方便后面的代码继续复用
                max_retries=3,  # 把右边计算出来的结果保存到 max_retries 变量中，方便后面的代码继续复用
                timeout=30,  # 把右边计算出来的结果保存到 timeout 变量中，方便后面的代码继续复用
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
        return self._llm  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    def _extract_keywords_fallback(self, query: str) -> list[str]:  # 定义函数 _extract_keywords_fallback，把一段可以复用的逻辑单独封装起来
        """无模型时的关键词兜底。

        这里不用 `split()`，因为中文问题通常没有空格。
        """

        raw_tokens = re.findall(r"[A-Za-z0-9_+\-.]{2,}|[\u4e00-\u9fff]{2,}", query)  # 把右边计算出来的结果保存到 raw_tokens 变量中，方便后面的代码继续复用
        keywords: list[str] = []  # 把右边计算出来的结果保存到 keywords 变量中，方便后面的代码继续复用
        seen: set[str] = set()  # 把右边计算出来的结果保存到 seen 变量中，方便后面的代码继续复用
        for token in raw_tokens:  # 开始遍历可迭代对象里的每一项，并对每一项执行同样的处理
            cleaned = token.strip()  # 把右边计算出来的结果保存到 cleaned 变量中，方便后面的代码继续复用
            if not cleaned or cleaned in seen:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                continue  # 跳过当前这一轮循环剩下的语句，直接开始下一轮
            seen.add(cleaned)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            keywords.append(cleaned)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            if len(keywords) >= 5:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                break  # 立刻结束当前循环，不再继续往后遍历
        return keywords or [query.strip()]  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    def _guess_category(self, query: str) -> str | None:  # 定义函数 _guess_category，把一段可以复用的逻辑单独封装起来
        """根据配置中的关键词规则猜测分类。"""

        scores: dict[str, int] = {}  # 把右边计算出来的结果保存到 scores 变量中，方便后面的代码继续复用
        for category, keywords in settings.SPIDER_CLASSIFICATION_RULES.items():  # 开始遍历可迭代对象里的每一项，并对每一项执行同样的处理
            score = sum(1 for keyword in keywords if keyword and keyword in query)  # 把右边计算出来的结果保存到 score 变量中，方便后面的代码继续复用
            if score > 0:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                scores[category] = score  # 把右边计算出来的结果保存到 scores[category] 变量中，方便后面的代码继续复用

        if not scores:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return None  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
        return max(scores.items(), key=lambda item: item[1])[0]  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    def _fallback(self, query: str, loop_count: int) -> AnalysisResult:  # 定义函数 _fallback，把一段可以复用的逻辑单独封装起来
        """在分析模型不可用时，使用规则方式生成检索条件。"""
        keywords = self._extract_keywords_fallback(query)  # 把右边计算出来的结果保存到 keywords 变量中，方便后面的代码继续复用
        category = self._guess_category(query)  # 把右边计算出来的结果保存到 category 变量中，方便后面的代码继续复用
        search_query = " ".join(keywords)  # 把右边计算出来的结果保存到 search_query 变量中，方便后面的代码继续复用

        # 重试时轻微放宽召回范围，但不再机械堆砌太多词。
        if loop_count > 0 and "新闻" not in search_query:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            search_query = f"{search_query} 新闻"  # 把右边计算出来的结果保存到 search_query 变量中，方便后面的代码继续复用

        return AnalysisResult(  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
            keywords=keywords,  # 把右边计算出来的结果保存到 keywords 变量中，方便后面的代码继续复用
            category=category,  # 把右边计算出来的结果保存到 category 变量中，方便后面的代码继续复用
            search_query=search_query,  # 把右边计算出来的结果保存到 search_query 变量中，方便后面的代码继续复用
        )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

    async def analyze(self, query: str, loop_count: int) -> AnalysisResult:  # 定义异步函数 analyze，调用它时通常需要配合 await 使用
        """调用分析模型或兜底逻辑，生成检索需要的结构化条件。"""
        llm = self._get_llm()  # 把右边计算出来的结果保存到 llm 变量中，方便后面的代码继续复用
        if llm is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return self._fallback(query, loop_count)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
            response = await llm.ainvoke(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
                [  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                    SystemMessage(content=self.SYSTEM_PROMPT),  # 把右边计算出来的结果保存到 SystemMessage(content 变量中，方便后面的代码继续复用
                    HumanMessage(content=query),  # 把右边计算出来的结果保存到 HumanMessage(content 变量中，方便后面的代码继续复用
                ]  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
            payload = _extract_json_payload(str(response.content))  # 把右边计算出来的结果保存到 payload 变量中，方便后面的代码继续复用
            keywords = payload.get("keywords") or []  # 把右边计算出来的结果保存到 keywords 变量中，方便后面的代码继续复用
            if isinstance(keywords, str):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                keywords = [keywords]  # 把右边计算出来的结果保存到 keywords 变量中，方便后面的代码继续复用
            keywords = [str(item).strip() for item in keywords if str(item).strip()]  # 把右边计算出来的结果保存到 keywords 变量中，方便后面的代码继续复用
            category = payload.get("category")  # 把右边计算出来的结果保存到 category 变量中，方便后面的代码继续复用
            if not keywords:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                return self._fallback(query, loop_count)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

            search_query = " ".join(keywords[:5])  # 把右边计算出来的结果保存到 search_query 变量中，方便后面的代码继续复用
            if loop_count > 0 and "新闻" not in search_query:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                search_query = f"{search_query} 新闻"  # 把右边计算出来的结果保存到 search_query 变量中，方便后面的代码继续复用

            return AnalysisResult(  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
                keywords=keywords[:5],  # 把右边计算出来的结果保存到 keywords 变量中，方便后面的代码继续复用
                category=category if isinstance(category, str) and category else None,  # 把右边计算出来的结果保存到 category 变量中，方便后面的代码继续复用
                search_query=search_query,  # 把右边计算出来的结果保存到 search_query 变量中，方便后面的代码继续复用
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
        except Exception:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
            logger.warning("分析模型执行失败，使用规则兜底", exc_info=True)  # 记录一条日志，方便后续排查程序运行过程和定位问题
            return self._fallback(query, loop_count)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


class GenerateService:  # 定义 GenerateService 类，用来把这一块相关的状态和行为组织在一起
    """回答生成服务。"""

    # 这里开始定义一个多行提示词字符串，后面几行都会作为模型提示内容的一部分
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

    def __init__(self) -> None:  # 定义函数 __init__，把一段可以复用的逻辑单独封装起来
        """初始化回答生成服务，并预留模型实例占位。"""
        self._llm: Optional[ChatOpenAI] = None  # 把右边计算出来的结果保存到 _llm 变量中，方便后面的代码继续复用

    def _get_llm(self) -> Optional[ChatOpenAI]:  # 定义函数 _get_llm，把一段可以复用的逻辑单独封装起来
        """按需创建回答生成模型，避免模块导入时立即初始化。"""
        if not settings.OPENAI_API_KEY:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return None  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        if self._llm is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            self._llm = ChatOpenAI(  # 把右边计算出来的结果保存到 _llm 变量中，方便后面的代码继续复用
                model=settings.LLM_GENERATE_MODEL,  # 把右边计算出来的结果保存到 model 变量中，方便后面的代码继续复用
                temperature=0.3,  # 把右边计算出来的结果保存到 temperature 变量中，方便后面的代码继续复用
                openai_api_key=settings.OPENAI_API_KEY,  # 把右边计算出来的结果保存到 openai_api_key 变量中，方便后面的代码继续复用
                openai_api_base=settings.OPENAI_API_BASE,  # 把右边计算出来的结果保存到 openai_api_base 变量中，方便后面的代码继续复用
                max_retries=3,  # 把右边计算出来的结果保存到 max_retries 变量中，方便后面的代码继续复用
                timeout=45,  # 把右边计算出来的结果保存到 timeout 变量中，方便后面的代码继续复用
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
        return self._llm  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    def build_context(self, news_list: list[dict[str, Any]], max_length: int = 2400) -> str:  # 定义函数 build_context，把一段可以复用的逻辑单独封装起来
        """把新闻列表压缩成模型上下文。"""

        if not news_list:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return "没有检索到相关新闻。"  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        parts: list[str] = []  # 把右边计算出来的结果保存到 parts 变量中，方便后面的代码继续复用
        total_length = 0  # 把右边计算出来的结果保存到 total_length 变量中，方便后面的代码继续复用
        for index, news in enumerate(news_list, start=1):  # 开始遍历可迭代对象里的每一项，并对每一项执行同样的处理
            title = news.get("title") or "无标题"  # 把右边计算出来的结果保存到 title 变量中，方便后面的代码继续复用
            description = news.get("description") or (news.get("content") or "")[:180]  # 把右边计算出来的结果保存到 description 变量中，方便后面的代码继续复用
            snippet = f"[新闻{index}] 标题：{title}\n摘要：{description}\n"  # 把右边计算出来的结果保存到 snippet 变量中，方便后面的代码继续复用
            if total_length + len(snippet) > max_length:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                break  # 立刻结束当前循环，不再继续往后遍历
            parts.append(snippet)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            total_length += len(snippet)  # 把右边计算出来的结果保存到 total_length + 变量中，方便后面的代码继续复用
        return "\n".join(parts)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    def fallback_answer(self, query: str, news_list: list[dict[str, Any]]) -> AnswerResult:  # 定义函数 fallback_answer，把一段可以复用的逻辑单独封装起来
        """模型不可用或解析失败时的规则兜底回答。"""

        if not news_list:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return AnswerResult(  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
                answer="抱歉，当前没有找到与您问题直接相关的新闻，请尝试换个问法再试。",  # 把右边计算出来的结果保存到 answer 变量中，方便后面的代码继续复用
                is_satisfied=False,  # 把右边计算出来的结果保存到 is_satisfied 变量中，方便后面的代码继续复用
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

        lines = ["根据当前检索到的新闻，我先为您整理到这些重点："]  # 把右边计算出来的结果保存到 lines 变量中，方便后面的代码继续复用
        for index, news in enumerate(news_list[:3], start=1):  # 开始遍历可迭代对象里的每一项，并对每一项执行同样的处理
            title = news.get("title") or "无标题"  # 把右边计算出来的结果保存到 title 变量中，方便后面的代码继续复用
            description = news.get("description") or (news.get("content") or "")[:80]  # 把右边计算出来的结果保存到 description 变量中，方便后面的代码继续复用
            lines.append(f"{index}. {title}：{description}")  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行

        if len(news_list) > 3:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            lines.append("还有更多相关新闻可继续展开。")  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行

        return AnswerResult(answer="\n".join(lines), is_satisfied=True)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    async def generate(  # 定义异步函数 generate，调用它时通常需要配合 await 使用
        self,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        query: str,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        news_list: list[dict[str, Any]],  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        loop_count: int,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        max_loops: int,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    ) -> AnswerResult:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
        """根据检索结果生成回答。"""

        llm = self._get_llm()  # 把右边计算出来的结果保存到 llm 变量中，方便后面的代码继续复用
        if llm is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return self.fallback_answer(query, news_list)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        context = self.build_context(news_list)  # 把右边计算出来的结果保存到 context 变量中，方便后面的代码继续复用
        user_prompt = f"用户问题：{query}\n\n相关新闻如下：\n{context}"  # 把右边计算出来的结果保存到 user_prompt 变量中，方便后面的代码继续复用

        try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
            response = await llm.ainvoke(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
                [  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                    SystemMessage(content=self.SYSTEM_PROMPT),  # 把右边计算出来的结果保存到 SystemMessage(content 变量中，方便后面的代码继续复用
                    HumanMessage(content=user_prompt),  # 把右边计算出来的结果保存到 HumanMessage(content 变量中，方便后面的代码继续复用
                ]  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
            payload = _extract_json_payload(str(response.content))  # 把右边计算出来的结果保存到 payload 变量中，方便后面的代码继续复用
            answer = str(payload.get("answer") or "").strip()  # 把右边计算出来的结果保存到 answer 变量中，方便后面的代码继续复用
            is_satisfied = bool(payload.get("is_satisfied", False))  # 把右边计算出来的结果保存到 is_satisfied 变量中，方便后面的代码继续复用

            if not answer:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                raise ValueError("模型没有返回 answer")  # 主动抛出异常，让上层知道这里出现了需要处理的问题

            if not is_satisfied and loop_count >= max_loops:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                # 达到最大重试次数后，给用户返回规则兜底，而不是死循环。
                return self.fallback_answer(query, news_list)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

            return AnswerResult(answer=answer, is_satisfied=is_satisfied)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
        except Exception:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
            logger.warning("回答模型执行失败，使用规则兜底", exc_info=True)  # 记录一条日志，方便后续排查程序运行过程和定位问题
            return self.fallback_answer(query, news_list)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


_analyze_service: Optional[AnalyzeService] = None  # 把右边计算出来的结果保存到 _analyze_service 变量中，方便后面的代码继续复用
_generate_service: Optional[GenerateService] = None  # 把右边计算出来的结果保存到 _generate_service 变量中，方便后面的代码继续复用


def get_analyze_service() -> AnalyzeService:  # 定义函数 get_analyze_service，把一段可以复用的逻辑单独封装起来
    """返回问题分析服务的全局单例。"""
    global _analyze_service  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    if _analyze_service is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        _analyze_service = AnalyzeService()  # 把右边计算出来的结果保存到 _analyze_service 变量中，方便后面的代码继续复用
    return _analyze_service  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


def get_generate_service() -> GenerateService:  # 定义函数 get_generate_service，把一段可以复用的逻辑单独封装起来
    """返回回答生成服务的全局单例。"""
    global _generate_service  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    if _generate_service is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        _generate_service = GenerateService()  # 把右边计算出来的结果保存到 _generate_service 变量中，方便后面的代码继续复用
    return _generate_service  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
