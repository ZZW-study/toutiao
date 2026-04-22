import { useQuery } from "@tanstack/react-query";

import { fetchChatResult } from "../../api/chat";

export function useChatResult(query: string) {
  const normalizedQuery = query.trim();

  return useQuery({
    queryKey: ["chat", normalizedQuery],
    queryFn: () => fetchChatResult(normalizedQuery),
    enabled: Boolean(normalizedQuery),
  });
}
