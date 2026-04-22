import { Link } from "react-router-dom";

import { formatPublishTime, formatViewCount } from "../app/format";
import type { NewsListItem } from "../api/types";
import { FavoriteButton } from "./FavoriteButton";

interface NewsFeedItemProps {
  actionSlot?: React.ReactNode;
  item: NewsListItem;
  label?: string;
  showFavorite?: boolean;
}

export function NewsFeedItem({
  actionSlot,
  item,
  label,
  showFavorite = true,
}: NewsFeedItemProps) {
  return (
    <article className="news-feed-item">
      <div className="news-feed-item__body">
        <div className="news-feed-item__copy">
          {label ? <p className="eyebrow">{label}</p> : null}

          <Link to={`/news/${item.id}`} className="news-feed-item__title">
            {item.title}
          </Link>

          <p className="news-feed-item__description">
            {item.description ?? "点击查看完整正文。"}
          </p>

          <div className="story-meta">
            <span>{item.author ?? "头条编辑部"}</span>
            <span>{formatPublishTime(item.publishTime)}</span>
            <span>{formatViewCount(item.views)}</span>
          </div>

          {actionSlot ? (
            <div className="news-feed-item__footer">{actionSlot}</div>
          ) : null}
        </div>

        <div className="news-feed-item__side">
          {item.image ? (
            <img src={item.image} alt={item.title} />
          ) : (
            <div className="news-feed-item__thumb-fallback">NEWS</div>
          )}
          {showFavorite ? <FavoriteButton newsId={item.id} /> : null}
        </div>
      </div>
    </article>
  );
}
