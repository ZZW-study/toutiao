import { Link } from "react-router-dom";

import { formatPublishTime, formatViewCount } from "../app/format";
import type { NewsListItem } from "../api/types";

interface LeadStoryProps {
  item: NewsListItem;
}

export function LeadStory({ item }: LeadStoryProps) {
  const heroStyle = item.image
    ? {
        backgroundImage: `linear-gradient(135deg, rgba(16, 16, 16, 0.12), rgba(16, 16, 16, 0.72)), url(${item.image})`,
      }
    : undefined;

  return (
    <article
      className={
        item.image
          ? "lead-story has-image"
          : "lead-story is-text-only"
      }
      style={heroStyle}
    >
      <div className="lead-story__content">
        <p className="eyebrow">Lead Story</p>
        <h2>{item.title}</h2>
        <p className="lead-story__description">
          {item.description ?? "打开正文，进入完整报道。"}
        </p>

        <div className="story-meta">
          <span>{item.author ?? "编辑部"}</span>
          <span>{formatPublishTime(item.publishTime)}</span>
          <span>{formatViewCount(item.views)}</span>
        </div>

        <Link to={`/news/${item.id}`} className="text-action">
          阅读全文
        </Link>
      </div>
    </article>
  );
}
