import { FormEvent, startTransition, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { splitParagraphs } from "../../app/format";
import { getErrorMessage } from "../../api/errors";
import { EmptyState } from "../../components/EmptyState";
import { ErrorNotice } from "../../components/ErrorNotice";
import { LoadingBlock } from "../../components/LoadingBlock";
import { NewsFeedItem } from "../../components/NewsFeedItem";
import { useChatResult } from "./hooks";

export function AskPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get("q")?.trim() ?? "";
  const [draft, setDraft] = useState(query);
  const chatQuery = useChatResult(query);

  useEffect(() => {
    setDraft(query);
  }, [query]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextQuery = draft.trim();

    startTransition(() => {
      if (nextQuery) {
        setSearchParams({ q: nextQuery });
        return;
      }

      setSearchParams({});
    });
  };

  return (
    <div className="page page--ask">
      <section className="ask-header">
        <div className="ask-header__copy">
          <p className="eyebrow">AI Briefing</p>
          <h1>像搜索一样提问，像编辑一样看结果。</h1>
          <p>
            输入问题后，左边得到结构化答案，右边拿到可继续阅读的相关新闻。
          </p>
        </div>

        <form className="ask-form" onSubmit={handleSubmit}>
          <label className="ask-form__label" htmlFor="ask-query">
            输入一个新闻问题
          </label>
          <textarea
            id="ask-query"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="例如：帮我总结今天的科技新闻重点"
          />
          <button type="submit" className="button button--primary">
            生成答案
          </button>
        </form>
      </section>

      {!query ? (
        <EmptyState
          title="还没有输入问题"
          description="先给 AI 一个问题，再查看总结和联读内容。"
        />
      ) : chatQuery.isLoading ? (
        <LoadingBlock label="AI 正在整理答案..." />
      ) : chatQuery.isError ? (
        <ErrorNotice
          title="问答暂时不可用"
          message={getErrorMessage(chatQuery.error)}
          onRetry={() => {
            void chatQuery.refetch();
          }}
        />
      ) : chatQuery.data ? (
        <section className="ask-result">
          <article className="answer-sheet">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Answer</p>
                <h2>AI 回答</h2>
              </div>
              <span>循环次数 {chatQuery.data.loopCount}</span>
            </div>
            <div className="answer-sheet__body">
              {splitParagraphs(chatQuery.data.answer).map((item) => (
                <p key={item}>{item}</p>
              ))}
            </div>
          </article>

          <aside className="answer-side">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Coverage</p>
                <h2>相关新闻</h2>
              </div>
            </div>

            {chatQuery.data.newsList.length ? (
              <div className="news-stream">
                {chatQuery.data.newsList.map((item) => (
                  <NewsFeedItem key={item.id} item={item} />
                ))}
              </div>
            ) : (
              <EmptyState
                title="没有关联新闻"
                description="当前问题没有返回联读条目。"
              />
            )}
          </aside>
        </section>
      ) : null}
    </div>
  );
}
