import { mapHistoryListResult } from "./mappers";
import { requestEnvelope } from "./client";
import type { HistoryListResult } from "./types";

export async function addHistory(newsId: number) {
  return requestEnvelope(
    "/api/history/add",
    {
      method: "POST",
      body: JSON.stringify({ newsId }),
    },
  );
}

export async function fetchHistory(
  page: number,
  pageSize = 10,
) {
  const query = new URLSearchParams({
    page: String(page),
    pageSize: String(pageSize),
  });

  const rawData = await requestEnvelope<unknown>(
    `/api/history/list?${query.toString()}`,
  );

  return mapHistoryListResult(rawData) as HistoryListResult;
}

export async function deleteHistoryItem(historyId: number) {
  return requestEnvelope(
    `/api/history/delete/${historyId}`,
    {
      method: "DELETE",
    },
  );
}

export async function clearHistory() {
  return requestEnvelope(
    "/api/history/clear",
    {
      method: "DELETE",
    },
  );
}
