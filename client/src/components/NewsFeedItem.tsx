import { Link } from "react-router-dom";

import { formatPublishTime, formatViewCount } from "../app/format";
import type { NewsListItem } from "../api/types";

interface NewsFeedItemProps {
  item: NewsListItem;
}

export function NewsFeedItem({ item }: NewsFeedItemProps) {
  return (
    <article className="news-feed-item">
      <div className="news-feed-item__content">
        <div className="story-meta">
          <span>{item.author ?? "编辑部"}</span>
          <span>{formatPublishTime(item.publishTime)}</span>
          <span>{formatViewCount(item.views)}</span>
        </div>

        <Link to={`/news/${item.id}`} className="news-feed-item__title">
          {item.title}
        </Link>

        <p className="news-feed-item__description">
          {item.description ?? "点击查看完整正文。"}
        </p>
      </div>
    </article>
  );
}
