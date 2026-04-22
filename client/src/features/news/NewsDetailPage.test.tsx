import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { jsonResponse } from "../../test/http";
import { renderApp } from "../../test/renderApp";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("NewsDetailPage", () => {
  it("renders the article body, checks favorite state, and records history for signed-in users", async () => {
    const fetchSpy = vi.fn((input: string | URL) => {
      const url = new URL(String(input));

      if (url.pathname === "/api/news/categories") {
        return jsonResponse({
          code: 200,
          message: "ok",
          data: [{ id: 1, name: "推荐" }],
        });
      }

      if (url.pathname === "/api/user/info") {
        return jsonResponse({
          code: 200,
          message: "ok",
          data: {
            id: 8,
            username: "reader",
            nickname: "读者",
            avatar: null,
            gender: null,
            bio: null,
            phone: null,
          },
        });
      }

      if (url.pathname === "/api/news/detail") {
        return jsonResponse({
          code: 200,
          message: "ok",
          data: {
            id: 101,
            title: "深夜快讯",
            content: "第一段\n第二段",
            author: "Desk",
            categoryId: 1,
            publishTime: "2026-04-22T10:00:00",
            views: 350,
            relatedNews: [
              {
                id: 102,
                title: "延伸阅读",
                description: "补充背景",
                categoryId: 1,
              },
            ],
          },
        });
      }

      if (url.pathname === "/api/favorite/check") {
        return jsonResponse({
          code: 200,
          message: "ok",
          data: {
            isFavorite: false,
          },
        });
      }

      if (url.pathname === "/api/history/add") {
        return jsonResponse({
          code: 200,
          message: "ok",
          data: {
            id: 21,
            userId: 8,
            newsId: 101,
            viewTime: "2026-04-22T10:05:00",
          },
        });
      }

      throw new Error(`Unhandled URL: ${url.toString()}`);
    });

    vi.stubGlobal("fetch", fetchSpy);

    renderApp(["/news/101"], {
      session: {
        token: "token-101",
        user: {
          id: 8,
          username: "reader",
          nickname: "读者",
          avatar: null,
          gender: null,
          bio: null,
          phone: null,
        },
      },
    });

    expect(
      await screen.findByRole("heading", { name: "深夜快讯" }),
    ).toBeInTheDocument();
    expect(screen.getByText("第一段")).toBeInTheDocument();
    expect(screen.getByText("延伸阅读")).toBeInTheDocument();

    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.some((call) =>
          String(call[0]).includes("/api/history/add"),
        ),
      ).toBe(true);
    });

    expect(
      screen.getAllByRole("button", { name: "收藏新闻" }).length,
    ).toBeGreaterThan(0);
  });

  it("renders a recoverable error state for 404 responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string | URL) => {
        const url = new URL(String(input));

        if (url.pathname === "/api/news/categories") {
          return jsonResponse({
            code: 200,
            message: "ok",
            data: [{ id: 1, name: "推荐" }],
          });
        }

        if (url.pathname === "/api/news/detail") {
          return jsonResponse(
            {
              code: 404,
              message: "新闻不存在",
              data: null,
            },
            404,
          );
        }

        throw new Error(`Unhandled URL: ${url.toString()}`);
      }),
    );

    renderApp(["/news/404"]);

    expect(
      await screen.findByRole("heading", { name: "新闻详情加载失败" }),
    ).toBeInTheDocument();
    expect(screen.getByText("新闻不存在")).toBeInTheDocument();
  });
});
