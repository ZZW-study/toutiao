import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";

import { createQueryClient } from "../app/queryClient";
import { AppShell } from "../components/AppShell";
import { AskPage } from "../features/chat/AskPage";
import { HomePage } from "../features/news/HomePage";
import { NewsDetailPage } from "../features/news/NewsDetailPage";

function LocationProbe() {
  const location = useLocation();

  return (
    <div data-testid="location-probe" style={{ display: "none" }}>
      {location.pathname}
      {location.search}
    </div>
  );
}

function TestRoot() {
  return (
    <>
      <AppShell />
      <LocationProbe />
    </>
  );
}

export function renderApp(initialEntries: string[] = ["/"]) {
  const queryClient = createQueryClient();

  const utils = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route element={<TestRoot />}>
            <Route index element={<HomePage />} />
            <Route path="/news/:id" element={<NewsDetailPage />} />
            <Route path="/ask" element={<AskPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  return {
    ...utils,
    queryClient,
  };
}
