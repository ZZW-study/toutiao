import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  addFavorite,
  checkFavorite,
  removeFavorite,
} from "../api/favorite";
import { useAuth } from "../features/auth/useAuth";

interface FavoriteButtonProps {
  newsId: number;
}

export function FavoriteButton({
  newsId,
}: FavoriteButtonProps) {
  const queryClient = useQueryClient();
  const { isAuthenticated, requireAuth, user } = useAuth();
  const favoriteStatusQuery = useQuery({
    queryKey: ["favorite-check", user?.id ?? 0, newsId],
    queryFn: () => checkFavorite(newsId),
    enabled: isAuthenticated,
    retry: false,
  });

  const favoriteMutation = useMutation({
    mutationFn: async () => {
      if (favoriteStatusQuery.data?.isFavorite) {
        await removeFavorite(newsId);
        return false;
      }

      await addFavorite(newsId);
      return true;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["favorite-check", user?.id ?? 0, newsId],
      });
      void queryClient.invalidateQueries({
        queryKey: ["favorite-list"],
      });
    },
  });

  const isFavorite = favoriteStatusQuery.data?.isFavorite ?? false;

  return (
    <button
      type="button"
      className={
        isFavorite
          ? "favorite-button is-active"
          : "favorite-button"
      }
      disabled={favoriteMutation.isPending}
      onClick={() => {
        if (!requireAuth("收藏功能需要登录后使用")) {
          return;
        }

        void favoriteMutation.mutateAsync();
      }}
      aria-label={isFavorite ? "取消收藏" : "收藏新闻"}
    >
      {favoriteMutation.isPending
        ? "处理中"
        : isFavorite
          ? "已收藏"
          : "收藏"}
    </button>
  );
}
