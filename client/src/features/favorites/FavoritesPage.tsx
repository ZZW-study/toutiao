import { startTransition } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { clearFavorites, fetchFavorites } from "../../api/favorite";
import { getErrorMessage } from "../../api/errors";
import { EmptyState } from "../../components/EmptyState";
import { ErrorNotice } from "../../components/ErrorNotice";
import { LoadingBlock } from "../../components/LoadingBlock";
import { NewsFeedItem } from "../../components/NewsFeedItem";
import { Pagination } from "../../components/Pagination";
import { AuthGate } from "../auth/AuthGate";
import { useAuth } from "../auth/useAuth";
import { formatPublishTime } from "../../app/format";

function parsePage(searchParams: URLSearchParams) {
  const rawValue = Number(searchParams.get("page") ?? "1");
  return Number.isInteger(rawValue) && rawValue > 0 ? rawValue : 1;
}

export function FavoritesPage() {
  const { isAuthenticated } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const page = parsePage(searchParams);

  const favoritesQuery = useQuery({
    queryKey: ["favorite-list", page],
    queryFn: () => fetchFavorites(page),
    enabled: isAuthenticated,
    retry: false,
  });

  const clearMutation = useMutation({
    mutationFn: clearFavorites,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["favorite-list"],
      });
    },
  });

  if (!isAuthenticated) {
    return (
      <div className="page">
        <AuthGate
          title="登录后查看收藏"
          description="收藏夹会同步保存你标记过的新闻。"
        />
      </div>
    );
  }

  return (
    <div className="page">
      <section className="page-head">
        <div>
          <p className="eyebrow">Favorites</p>
          <h1>我的收藏</h1>
          <p>把想回看的报道留在这里，稍后继续阅读。</p>
        </div>
        <button
          type="button"
          className="button button--ghost"
          disabled={clearMutation.isPending}
          onClick={() => {
            void clearMutation.mutateAsync();
          }}
        >
          {clearMutation.isPending ? "清空中..." : "清空收藏"}
        </button>
      </section>

      {favoritesQuery.isLoading ? (
        <LoadingBlock label="正在加载收藏夹..." />
      ) : favoritesQuery.isError ? (
        <ErrorNotice
          title="收藏夹加载失败"
          message={getErrorMessage(favoritesQuery.error)}
          onRetry={() => {
            void favoritesQuery.refetch();
          }}
        />
      ) : favoritesQuery.data?.list.length ? (
        <>
          <div className="news-stream">
            {favoritesQuery.data.list.map((item) => (
              <NewsFeedItem
                key={item.favoriteId}
                item={item}
                label={`收藏于 ${formatPublishTime(item.favoriteTime)}`}
              />
            ))}
          </div>
          <Pagination
            page={page}
            total={favoritesQuery.data.total}
            hasMore={favoritesQuery.data.hasMore}
            onPageChange={(nextPage) => {
              const nextSearchParams = new URLSearchParams(searchParams);
              nextSearchParams.set("page", String(nextPage));
              startTransition(() => {
                setSearchParams(nextSearchParams);
              });
            }}
          />
        </>
      ) : (
        <EmptyState
          title="收藏夹还是空的"
          description="在新闻卡片或正文页点一下收藏，内容就会出现在这里。"
        />
      )}
    </div>
  );
}
