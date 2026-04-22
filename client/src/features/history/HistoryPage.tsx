import { startTransition } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { formatPublishTime } from "../../app/format";
import { getErrorMessage } from "../../api/errors";
import {
  clearHistory,
  deleteHistoryItem,
  fetchHistory,
} from "../../api/history";
import { EmptyState } from "../../components/EmptyState";
import { ErrorNotice } from "../../components/ErrorNotice";
import { FavoriteButton } from "../../components/FavoriteButton";
import { LoadingBlock } from "../../components/LoadingBlock";
import { Pagination } from "../../components/Pagination";
import { AuthGate } from "../auth/AuthGate";
import { useAuth } from "../auth/useAuth";

function parsePage(searchParams: URLSearchParams) {
  const rawValue = Number(searchParams.get("page") ?? "1");
  return Number.isInteger(rawValue) && rawValue > 0 ? rawValue : 1;
}

export function HistoryPage() {
  const { isAuthenticated } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const page = parsePage(searchParams);

  const historyQuery = useQuery({
    queryKey: ["history-list", page],
    queryFn: () => fetchHistory(page),
    enabled: isAuthenticated,
    retry: false,
  });

  const clearMutation = useMutation({
    mutationFn: clearHistory,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["history-list"],
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteHistoryItem,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["history-list"],
      });
    },
  });

  if (!isAuthenticated) {
    return (
      <div className="page">
        <AuthGate
          title="登录后查看浏览历史"
          description="阅读过的新闻会自动记录到这里，方便稍后回看。"
        />
      </div>
    );
  }

  return (
    <div className="page">
      <section className="page-head">
        <div>
          <p className="eyebrow">History</p>
          <h1>浏览历史</h1>
          <p>正文页在登录状态下会自动写入历史，按时间倒序排列。</p>
        </div>
        <button
          type="button"
          className="button button--ghost"
          disabled={clearMutation.isPending}
          onClick={() => {
            void clearMutation.mutateAsync();
          }}
        >
          {clearMutation.isPending ? "清空中..." : "清空历史"}
        </button>
      </section>

      {historyQuery.isLoading ? (
        <LoadingBlock label="正在加载浏览历史..." />
      ) : historyQuery.isError ? (
        <ErrorNotice
          title="浏览历史加载失败"
          message={getErrorMessage(historyQuery.error)}
          onRetry={() => {
            void historyQuery.refetch();
          }}
        />
      ) : historyQuery.data?.list.length ? (
        <>
          <div className="history-list">
            {historyQuery.data.list.map((item) => (
              <article key={item.historyId} className="history-item">
                <div className="history-item__body">
                  <p className="eyebrow">
                    浏览于 {formatPublishTime(item.viewTime)}
                  </p>
                  <Link
                    to={`/news/${item.id}`}
                    className="history-item__title"
                  >
                    {item.title}
                  </Link>
                  <p className="history-item__description">
                    {item.description ?? "点击回到正文继续阅读。"}
                  </p>
                  <div className="history-item__actions">
                    <Link
                      to={`/news/${item.id}`}
                      className="button button--primary"
                    >
                      继续阅读
                    </Link>
                    <FavoriteButton newsId={item.id} />
                    <button
                      type="button"
                      className="button button--ghost"
                      disabled={deleteMutation.isPending}
                      onClick={() => {
                        void deleteMutation.mutateAsync(item.historyId);
                      }}
                    >
                      删除记录
                    </button>
                  </div>
                </div>
                {item.image ? (
                  <img
                    src={item.image}
                    alt={item.title}
                    className="history-item__thumb"
                  />
                ) : null}
              </article>
            ))}
          </div>
          <Pagination
            page={page}
            total={historyQuery.data.total}
            hasMore={historyQuery.data.hasMore}
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
          title="还没有浏览历史"
          description="打开一篇新闻正文后，这里就会自动出现对应记录。"
        />
      )}
    </div>
  );
}
