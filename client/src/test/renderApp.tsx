import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";

import type { UserInfo } from "../api/types";
import { createQueryClient } from "../app/queryClient";
import { setStoredSession } from "../app/sessionStore";
import { AppShell } from "../components/AppShell";
import { AuthProvider } from "../features/auth/AuthProvider";
import { AskPage } from "../features/chat/AskPage";
import { FavoritesPage } from "../features/favorites/FavoritesPage";
import { HistoryPage } from "../features/history/HistoryPage";
import { HomePage } from "../features/news/HomePage";
import { NewsDetailPage } from "../features/news/NewsDetailPage";
import { ProfilePage } from "../features/profile/ProfilePage";

function LocationProbe() {
  const location = useLocation();

  return (
    <div data-testid="location-probe" style={{ display: "none" }}>
      {location.pathname}
      {location.search}
    </div>
  );
}

function TestLayout() {
  return (
    <>
      <AppShell />
      <LocationProbe />
    </>
  );
}

export function renderApp(
  initialEntries: string[] = ["/"],
  options?: {
    session?: {
      token: string;
      user: UserInfo;
    };
  },
) {
  setStoredSession(
    options?.session
      ? {
          token: options.session.token,
          user: options.session.user,
        }
      : null,
  );

  const queryClient = createQueryClient();

  const utils = render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter
          initialEntries={initialEntries}
          future={{
            v7_relativeSplatPath: true,
            v7_startTransition: true,
          }}
        >
          <Routes>
            <Route element={<TestLayout />}>
              <Route index element={<HomePage />} />
              <Route path="/news/:id" element={<NewsDetailPage />} />
              <Route path="/ask" element={<AskPage />} />
              <Route path="/favorites" element={<FavoritesPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/profile" element={<ProfilePage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );

  return {
    ...utils,
    queryClient,
  };
}
