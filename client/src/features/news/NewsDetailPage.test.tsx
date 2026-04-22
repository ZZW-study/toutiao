import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { jsonResponse } from "../../test/http";
import { renderApp } from "../../test/renderApp";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("NewsDetailPage", () => {
  it("renders the article body and related stories", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        jsonResponse({
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
        }),
      ),
    );

    renderApp(["/news/101"]);

    expect(
      await screen.findByRole("heading", { name: "深夜快讯" }),
    ).toBeInTheDocument();
    expect(screen.getByText("第一段")).toBeInTheDocument();
    expect(screen.getByText("延伸阅读")).toBeInTheDocument();
  });

  it("renders a recoverable error state for 404 responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        jsonResponse(
          {
            code: 404,
            message: "新闻不存在",
            data: null,
          },
          404,
        ),
      ),
    );

    renderApp(["/news/404"]);

    expect(
      await screen.findByRole("heading", { name: "新闻详情加载失败" }),
    ).toBeInTheDocument();
    expect(screen.getByText("新闻不存在")).toBeInTheDocument();
  });
});
