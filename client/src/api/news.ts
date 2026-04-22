import {
  mapNewsCategory,
  mapNewsDetail,
  mapNewsListResult,
} from "./mappers";
import { requestEnvelope } from "./client";
import type {
  NewsCategory,
  NewsDetail,
  NewsListResult,
} from "./types";

export async function fetchNewsCategories() {
  const rawData = await requestEnvelope<unknown[]>("/api/news/categories");
  return Array.isArray(rawData)
    ? rawData
        .map(mapNewsCategory)
        .filter(
          (item): item is NewsCategory => item !== null,
        )
    : [];
}

export async function fetchNewsList(
  categoryId: number,
  page: number,
  pageSize = 10,
) {
  const query = new URLSearchParams({
    categoryId: String(categoryId),
    page: String(page),
    pageSize: String(pageSize),
  });

  const rawData = await requestEnvelope<unknown>(
    `/api/news/list?${query.toString()}`,
  );

  return mapNewsListResult(rawData) as NewsListResult;
}

export async function fetchNewsDetail(newsId: number) {
  const query = new URLSearchParams({
    id: String(newsId),
  });
  const rawData = await requestEnvelope<unknown>(
    `/api/news/detail?${query.toString()}`,
  );

  return mapNewsDetail(rawData) as NewsDetail;
}
