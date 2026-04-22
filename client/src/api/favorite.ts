import {
  mapFavoriteListResult,
  mapFavoriteStatus,
} from "./mappers";
import { requestEnvelope } from "./client";
import type {
  FavoriteListResult,
  FavoriteStatus,
} from "./types";

export async function checkFavorite(newsId: number) {
  const query = new URLSearchParams({
    newsId: String(newsId),
  });

  const rawData = await requestEnvelope<unknown>(
    `/api/favorite/check?${query.toString()}`,
  );

  return mapFavoriteStatus(rawData) as FavoriteStatus;
}

export async function addFavorite(newsId: number) {
  return requestEnvelope(
    "/api/favorite/add",
    {
      method: "POST",
      body: JSON.stringify({ newsId }),
    },
  );
}

export async function removeFavorite(newsId: number) {
  const query = new URLSearchParams({
    newsId: String(newsId),
  });

  return requestEnvelope(
    `/api/favorite/remove?${query.toString()}`,
    {
      method: "DELETE",
    },
  );
}

export async function fetchFavorites(
  page: number,
  pageSize = 10,
) {
  const query = new URLSearchParams({
    page: String(page),
    pageSize: String(pageSize),
  });

  const rawData = await requestEnvelope<unknown>(
    `/api/favorite/list?${query.toString()}`,
  );

  return mapFavoriteListResult(rawData) as FavoriteListResult;
}

export async function clearFavorites() {
  return requestEnvelope(
    "/api/favorite/clear",
    {
      method: "DELETE",
    },
  );
}
