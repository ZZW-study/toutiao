import {
  createBrowserRouter,
  type RouteObject,
} from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { AskPage } from "../features/chat/AskPage";
import { HomePage } from "../features/news/HomePage";
import { NewsDetailPage } from "../features/news/NewsDetailPage";

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
    ],
  },
];

export function createAppRouter() {
  return createBrowserRouter(appRoutes);
}
