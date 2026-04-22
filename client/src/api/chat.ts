import { requestRaw } from "./client";
import { mapChatResult } from "./mappers";
import type { ChatResult } from "./types";

export async function fetchChatResult(query: string) {
  const rawData = await requestRaw<unknown>("/chat/", {
    method: "POST",
    body: JSON.stringify({ query }),
  });

  return mapChatResult(rawData) as ChatResult;
}
