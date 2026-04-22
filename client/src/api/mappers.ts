import type {
  ChatResult,
  NewsCategory,
  NewsDetail,
  NewsListItem,
  NewsListResult,
} from "./types";

const EMPTY_NEWS_LIST: NewsListResult = {
  list: [],
  total: 0,
  hasMore: false,
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object";
}

function pickFirst(
  value: Record<string, unknown>,
  keys: string[],
) {
  for (const key of keys) {
    if (key in value) {
      return value[key];
    }
  }

  return undefined;
}

function asNumber(value: unknown, fallback = 0) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return fallback;
}

function asNullableString(value: unknown) {
  if (typeof value !== "string") {
    return null;
  }

  const nextValue = value.trim();
  return nextValue ? nextValue : null;
}

function asString(value: unknown, fallback = "") {
  return asNullableString(value) ?? fallback;
}

function resolvePublishTime(value: Record<string, unknown>) {
  return asNullableString(
    pickFirst(value, ["publishTime", "publishedTime", "publish_time"]),
  );
}

function resolveCategoryId(value: Record<string, unknown>) {
  return asNumber(
    pickFirst(value, ["categoryId", "category_id"]),
    0,
  );
}

function resolveHasMore(value: Record<string, unknown>) {
  const rawValue = pickFirst(value, ["hasMore", "has_more"]);

  if (typeof rawValue === "boolean") {
    return rawValue;
  }

  if (typeof rawValue === "string") {
    return rawValue === "true";
  }

  return Boolean(rawValue);
}

export function mapNewsCategory(raw: unknown): NewsCategory | null {
  if (!isRecord(raw)) {
    return null;
  }

  const id = asNumber(raw.id, 0);
  const name = asString(raw.name);
  if (!id || !name) {
    return null;
  }

  return { id, name };
}

export function mapNewsItem(raw: unknown): NewsListItem | null {
  if (!isRecord(raw)) {
    return null;
  }

  const id = asNumber(raw.id, 0);
  const title = asString(raw.title);

  if (!id || !title) {
    return null;
  }

  return {
    id,
    title,
    description:
      asNullableString(raw.description) ??
      asNullableString(raw.content) ??
      null,
    image: asNullableString(raw.image),
    author: asNullableString(raw.author),
    categoryId: resolveCategoryId(raw),
    views: asNumber(raw.views, 0),
    publishTime: resolvePublishTime(raw),
  };
}

export function mapNewsListResult(raw: unknown): NewsListResult {
  if (!isRecord(raw)) {
    return EMPTY_NEWS_LIST;
  }

  const rawList = Array.isArray(raw.list) ? raw.list : [];

  return {
    list: rawList
      .map(mapNewsItem)
      .filter((item): item is NewsListItem => item !== null),
    total: asNumber(raw.total, rawList.length),
    hasMore: resolveHasMore(raw),
  };
}

export function mapNewsDetail(raw: unknown): NewsDetail {
  if (!isRecord(raw)) {
    throw new Error("新闻详情格式错误");
  }

  const mappedItem = mapNewsItem(raw);
  if (!mappedItem) {
    throw new Error("新闻详情格式错误");
  }

  const rawRelatedNews = Array.isArray(raw.relatedNews)
    ? raw.relatedNews
    : Array.isArray(raw.related_news)
      ? raw.related_news
      : [];

  return {
    ...mappedItem,
    content: asString(raw.content),
    relatedNews: rawRelatedNews
      .map(mapNewsItem)
      .filter((item): item is NewsListItem => item !== null),
  };
}

export function mapChatResult(raw: unknown): ChatResult {
  if (!isRecord(raw)) {
    throw new Error("问答结果格式错误");
  }

  const rawNewsList = Array.isArray(raw.news_list)
    ? raw.news_list
    : Array.isArray(raw.newsList)
      ? raw.newsList
      : [];

  return {
    answer: asString(raw.answer),
    newsList: rawNewsList
      .map(mapNewsItem)
      .filter((item): item is NewsListItem => item !== null),
    loopCount: asNumber(
      pickFirst(raw, ["loop_count", "loopCount"]),
      0,
    ),
  };
}
