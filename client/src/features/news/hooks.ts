import { useQuery } from "@tanstack/react-query";

import {
  fetchNewsCategories,
  fetchNewsDetail,
  fetchNewsList,
} from "../../api/news";

export const PAGE_SIZE = 10;

export function useCategories() {
  return useQuery({
    queryKey: ["categories"],
    queryFn: fetchNewsCategories,
  });
}

export function useNewsList(
  categoryId: number,
  page: number,
  enabled = true,
) {
  return useQuery({
    queryKey: ["news-list", categoryId, page],
    queryFn: () => fetchNewsList(categoryId, page, PAGE_SIZE),
    enabled,
    retry: false,
  });
}

export function useNewsDetail(
  newsId: number,
  enabled = true,
) {
  return useQuery({
    queryKey: ["news-detail", newsId],
    queryFn: () => fetchNewsDetail(newsId),
    enabled,
    retry: false,
  });
}
