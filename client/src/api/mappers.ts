import type {
  AuthSession,
  ChatResult,
  FavoriteItem,
  FavoriteListResult,
  FavoriteStatus,
  HistoryItem,
  HistoryListResult,
  NewsCategory,
  NewsDetail,
  NewsListItem,
  NewsListResult,
  UserInfo,
} from "./types";

const EMPTY_NEWS_LIST: NewsListResult = {
  list: [],
  total: 0,
  hasMore: false,
};

const EMPTY_FAVORITE_LIST: FavoriteListResult = {
  list: [],
  total: 0,
  hasMore: false,
};

const EMPTY_HISTORY_LIST: HistoryListResult = {
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

function asBoolean(value: unknown, fallback = false) {
  if (typeof value === "boolean") {
    return value;
  }

  if (typeof value === "string") {
    return value === "true";
  }

  if (typeof value === "number") {
    return value !== 0;
  }

  return fallback;
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
  return asBoolean(
    pickFirst(value, ["hasMore", "has_more"]),
    false,
  );
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

export function mapUserInfo(raw: unknown): UserInfo {
  if (!isRecord(raw)) {
    throw new Error("用户信息格式错误");
  }

  const id = asNumber(raw.id, 0);
  const username = asString(raw.username);

  if (!id || !username) {
    throw new Error("用户信息格式错误");
  }

  return {
    id,
    username,
    nickname: asNullableString(raw.nickname),
    avatar: asNullableString(raw.avatar),
    gender: asNullableString(raw.gender),
    bio: asNullableString(raw.bio),
    phone: asNullableString(raw.phone),
  };
}

export function mapAuthSession(raw: unknown): AuthSession {
  if (!isRecord(raw)) {
    throw new Error("登录结果格式错误");
  }

  const token = asString(raw.token);
  const userInfo = mapUserInfo(
    pickFirst(raw, ["userInfo", "user_info"]),
  );

  if (!token) {
    throw new Error("登录结果格式错误");
  }

  return { token, userInfo };
}

export function mapFavoriteStatus(raw: unknown): FavoriteStatus {
  if (!isRecord(raw)) {
    return { isFavorite: false };
  }

  return {
    isFavorite: asBoolean(
      pickFirst(raw, ["isFavorite", "is_favorite"]),
      false,
    ),
  };
}

export function mapFavoriteItem(raw: unknown): FavoriteItem | null {
  const baseItem = mapNewsItem(raw);
  if (!baseItem || !isRecord(raw)) {
    return null;
  }

  const favoriteId = asNumber(
    pickFirst(raw, ["favoriteId", "favorite_id"]),
    0,
  );

  if (!favoriteId) {
    return null;
  }

  return {
    ...baseItem,
    favoriteId,
    favoriteTime: asNullableString(
      pickFirst(raw, ["favoriteTime", "favorite_time"]),
    ),
  };
}

export function mapFavoriteListResult(raw: unknown): FavoriteListResult {
  if (!isRecord(raw)) {
    return EMPTY_FAVORITE_LIST;
  }

  const rawList = Array.isArray(raw.list) ? raw.list : [];

  return {
    list: rawList
      .map(mapFavoriteItem)
      .filter((item): item is FavoriteItem => item !== null),
    total: asNumber(raw.total, rawList.length),
    hasMore: resolveHasMore(raw),
  };
}

export function mapHistoryItem(raw: unknown): HistoryItem | null {
  const baseItem = mapNewsItem(raw);
  if (!baseItem || !isRecord(raw)) {
    return null;
  }

  const historyId = asNumber(
    pickFirst(raw, ["historyId", "history_id"]),
    0,
  );

  if (!historyId) {
    return null;
  }

  return {
    ...baseItem,
    historyId,
    viewTime: asNullableString(
      pickFirst(raw, ["viewTime", "view_time"]),
    ),
  };
}

export function mapHistoryListResult(raw: unknown): HistoryListResult {
  if (!isRecord(raw)) {
    return EMPTY_HISTORY_LIST;
  }

  const rawList = Array.isArray(raw.list) ? raw.list : [];

  return {
    list: rawList
      .map(mapHistoryItem)
      .filter((item): item is HistoryItem => item !== null),
    total: asNumber(raw.total, rawList.length),
    hasMore: resolveHasMore(raw),
  };
}
