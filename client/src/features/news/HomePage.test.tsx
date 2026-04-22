import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { jsonResponse } from "../../test/http";
import { renderApp } from "../../test/renderApp";

const categoriesPayload = [
  { id: 1, name: "要闻" },
  { id: 7, name: "科技" },
];

function createNewsEnvelope(list: Array<Record<string, unknown>>, hasMore = false) {
  return {
    code: 200,
    message: "ok",
    data: {
      list,
      total: list.length,
      hasMore,
    },
  };
}

function installHomeApi(listMap: Record<string, unknown>) {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string | URL) => {
      const url = new URL(String(input));

      if (url.pathname === "/api/news/categories") {
        return jsonResponse({
          code: 200,
          message: "ok",
          data: categoriesPayload,
        });
      }

      if (url.pathname === "/api/news/list") {
        const key = `${url.searchParams.get("categoryId")}-${url.searchParams.get("page")}`;
        const payload = listMap[key];

        if (!payload) {
          return jsonResponse(createNewsEnvelope([]));
        }

        return jsonResponse(payload);
      }

      throw new Error(`Unhandled URL: ${url.toString()}`);
    }),
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("HomePage", () => {
  it("selects the first category and loads the first page", async () => {
    installHomeApi({
      "1-1": createNewsEnvelope([
        {
          id: 11,
          title: "测试焦点新闻",
          description: "焦点摘要",
          author: "Desk",
          categoryId: 1,
          views: 120,
          publishTime: "2026-04-22T08:00:00",
        },
        {
          id: 12,
          title: "后续追踪",
          description: "第二条摘要",
          categoryId: 1,
          views: 56,
        },
      ]),
    });

    renderApp(["/"]);

    await waitFor(() => {
      expect(screen.getByTestId("location-probe")).toHaveTextContent(
        "/?category=1&page=1",
      );
    });

    expect(
      await screen.findByRole("heading", { name: "测试焦点新闻" }),
    ).toBeInTheDocument();
    expect(screen.getByText("后续追踪")).toBeInTheDocument();
  });

  it("syncs category switches into the url and data", async () => {
    installHomeApi({
      "1-1": createNewsEnvelope([
        {
          id: 11,
          title: "测试焦点新闻",
          description: "焦点摘要",
          categoryId: 1,
        },
      ]),
      "7-1": createNewsEnvelope([
        {
          id: 21,
          title: "量子芯片夜读",
          description: "科技摘要",
          category_id: 7,
        },
      ]),
    });

    const user = userEvent.setup();
    renderApp(["/?category=1&page=1"]);

    expect(
      await screen.findByRole("heading", { name: "测试焦点新闻" }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "科技" }));

    await waitFor(() => {
      expect(screen.getByTestId("location-probe")).toHaveTextContent(
        "/?category=7&page=1",
      );
    });

    expect(
      await screen.findByRole("heading", { name: "量子芯片夜读" }),
    ).toBeInTheDocument();
  });

  it("syncs pagination into the url and fetches the next page", async () => {
    installHomeApi({
      "1-1": createNewsEnvelope(
        [
          {
            id: 11,
            title: "测试焦点新闻",
            description: "焦点摘要",
            categoryId: 1,
          },
          {
            id: 12,
            title: "后续追踪",
            description: "第二条摘要",
            categoryId: 1,
          },
        ],
        true,
      ),
      "1-2": createNewsEnvelope([
        {
          id: 13,
          title: "第二页条目",
          description: "第二页摘要",
          categoryId: 1,
        },
      ]),
    });

    const user = userEvent.setup();
    renderApp(["/?category=1&page=1"]);

    expect(await screen.findByText("后续追踪")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "下一页" }));

    await waitFor(() => {
      expect(screen.getByTestId("location-probe")).toHaveTextContent(
        "/?category=1&page=2",
      );
    });

    expect(await screen.findByText("第二页条目")).toBeInTheDocument();
  });

  it("shows a structured empty state when the list is empty", async () => {
    installHomeApi({
      "1-1": createNewsEnvelope([]),
    });

    renderApp(["/?category=1&page=1"]);

    expect(
      await screen.findByRole("heading", { name: "当前栏目还没有内容" }),
    ).toBeInTheDocument();
  });
});
