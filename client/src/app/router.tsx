import {
  createBrowserRouter,
  type RouteObject,
} from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { AskPage } from "../features/chat/AskPage";
import { FavoritesPage } from "../features/favorites/FavoritesPage";
import { HistoryPage } from "../features/history/HistoryPage";
import { HomePage } from "../features/news/HomePage";
import { NewsDetailPage } from "../features/news/NewsDetailPage";
import { ProfilePage } from "../features/profile/ProfilePage";

export const appRoutes: RouteObject[] = [
  {
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: "news/:id",
        element: <NewsDetailPage />,
      },
      {
        path: "ask",
        element: <AskPage />,
      },
      {
        path: "favorites",
        element: <FavoritesPage />,
      },
      {
        path: "history",
        element: <HistoryPage />,
      },
      {
        path: "profile",
        element: <ProfilePage />,
      },
    ],
  },
];

export function createAppRouter() {
  return createBrowserRouter(appRoutes);
}
