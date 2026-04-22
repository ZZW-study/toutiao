import { Link, useParams } from "react-router-dom";

import {
  formatPublishTime,
  formatViewCount,
  splitParagraphs,
} from "../../app/format";
import { getErrorMessage } from "../../api/errors";
import { EmptyState } from "../../components/EmptyState";
import { ErrorNotice } from "../../components/ErrorNotice";
import { LoadingBlock } from "../../components/LoadingBlock";
import { NewsFeedItem } from "../../components/NewsFeedItem";
import { useNewsDetail } from "./hooks";

export function NewsDetailPage() {
  const { id } = useParams();
  const newsId = Number(id);
  const isValidId = Number.isInteger(newsId) && newsId > 0;
  const detailQuery = useNewsDetail(newsId, isValidId);

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
    <article className="page page--article">
      <header className="article-head reveal">
        <Link to="/" className="back-link">
          返回新闻首页
        </Link>
        <p className="eyebrow">Story File</p>
        <h1>{detailQuery.data.title}</h1>
        <div className="story-meta">
          <span>{detailQuery.data.author ?? "编辑部"}</span>
          <span>
            {formatPublishTime(detailQuery.data.publishTime)}
          </span>
          <span>{formatViewCount(detailQuery.data.views)}</span>
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

      <section className="related-panel">
        <div className="section-heading">
          <p className="eyebrow">Related News</p>
          <h2>继续阅读</h2>
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
      </section>
    </article>
  );
}
