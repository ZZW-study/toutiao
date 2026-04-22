import { useEffect, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import {
  formatPublishTime,
  formatViewCount,
  splitParagraphs,
} from "../../app/format";
import { addHistory } from "../../api/history";
import { getErrorMessage } from "../../api/errors";
import { EmptyState } from "../../components/EmptyState";
import { ErrorNotice } from "../../components/ErrorNotice";
import { FavoriteButton } from "../../components/FavoriteButton";
import { LoadingBlock } from "../../components/LoadingBlock";
import { NewsFeedItem } from "../../components/NewsFeedItem";
import { useAuth } from "../auth/useAuth";
import { useNewsDetail } from "./hooks";

export function NewsDetailPage() {
  const { id } = useParams();
  const { isAuthenticated } = useAuth();
  const newsId = Number(id);
  const isValidId = Number.isInteger(newsId) && newsId > 0;
  const detailQuery = useNewsDetail(newsId, isValidId);
  const recordedNewsId = useRef<number | null>(null);
  const historyMutation = useMutation({
    mutationFn: addHistory,
  });

  useEffect(() => {
    if (
      !isAuthenticated ||
      !detailQuery.data ||
      recordedNewsId.current === newsId
    ) {
      return;
    }

    recordedNewsId.current = newsId;
    void historyMutation.mutateAsync(newsId).catch(() => {});
  }, [
    detailQuery.data,
    historyMutation,
    isAuthenticated,
    newsId,
  ]);

  if (!isValidId) {
    return (
      <div className="page">
        <ErrorNotice
          title="新闻详情加载失败"
          message="无效的新闻编号。"
        />
      </div>
    );
  }

  if (detailQuery.isLoading) {
    return (
      <div className="page">
        <LoadingBlock label="正在打开新闻正文..." />
      </div>
    );
  }

  if (detailQuery.isError) {
    return (
      <div className="page">
        <ErrorNotice
          title="新闻详情加载失败"
          message={getErrorMessage(detailQuery.error)}
          onRetry={() => {
            void detailQuery.refetch();
          }}
        />
      </div>
    );
  }

  if (!detailQuery.data) {
    return (
      <div className="page">
        <EmptyState
          title="正文暂未找到"
          description="这篇新闻可能已经下线，请返回首页继续浏览。"
        />
      </div>
    );
  }

  const paragraphs = splitParagraphs(detailQuery.data.content);

  return (
    <article className="page page--detail">
      <div className="detail-layout">
        <section className="detail-main">
          <header className="article-head">
            <Link to="/" className="back-link">
              返回首页
            </Link>
            <p className="eyebrow">Story</p>
            <h1>{detailQuery.data.title}</h1>
            <div className="story-meta">
              <span>{detailQuery.data.author ?? "头条编辑部"}</span>
              <span>{formatPublishTime(detailQuery.data.publishTime)}</span>
              <span>{formatViewCount(detailQuery.data.views)}</span>
            </div>
            <div className="article-head__actions">
              <FavoriteButton newsId={detailQuery.data.id} />
            </div>
          </header>

          {detailQuery.data.image ? (
            <div className="article-visual">
              <img
                src={detailQuery.data.image}
                alt={detailQuery.data.title}
              />
            </div>
          ) : null}

          <section className="article-body">
            {paragraphs.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </section>
        </section>

        <aside className="detail-side">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Related</p>
              <h2>继续阅读</h2>
            </div>
          </div>
          {detailQuery.data.relatedNews.length ? (
            <div className="news-stream">
              {detailQuery.data.relatedNews.map((item) => (
                <NewsFeedItem key={item.id} item={item} />
              ))}
            </div>
          ) : (
            <EmptyState
              title="暂无相关推荐"
              description="这篇报道暂时没有更多联读内容。"
            />
          )}
        </aside>
      </div>
    </article>
  );
}
