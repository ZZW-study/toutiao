import { Link } from "react-router-dom";

import { formatPublishTime, formatViewCount } from "../app/format";
import type { NewsListItem } from "../api/types";
import { FavoriteButton } from "./FavoriteButton";

interface LeadStoryProps {
  item: NewsListItem;
}

export function LeadStory({ item }: LeadStoryProps) {
  return (
    <article className="lead-story">
      <div className="lead-story__visual">
        {item.image ? (
          <img src={item.image} alt={item.title} />
        ) : (
          <div className="lead-story__fallback">TOP STORY</div>
        )}
      </div>

      <div className="lead-story__content">
        <p className="eyebrow">Top Story</p>
        <h2>{item.title}</h2>
        <p className="lead-story__description">
          {item.description ?? "打开正文，继续阅读完整报道。"}
        </p>

        <div className="story-meta">
          <span>{item.author ?? "头条编辑部"}</span>
          <span>{formatPublishTime(item.publishTime)}</span>
          <span>{formatViewCount(item.views)}</span>
        </div>

        <div className="lead-story__actions">
          <Link to={`/news/${item.id}`} className="button button--primary">
            阅读全文
          </Link>
          <FavoriteButton newsId={item.id} />
        </div>
      </div>
    </article>
  );
}
