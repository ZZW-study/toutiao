import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchChatResult } from "./chat";
import { ApiError } from "./errors";
import { fetchNewsCategories, fetchNewsList } from "./news";

function mockFetchResponse(body: unknown, status = 200) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify(body), {
        status,
        headers: {
          "Content-Type": "application/json",
        },
      }),
    ),
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("api adapters", () => {
  it("parses envelope success responses", async () => {
    mockFetchResponse({
      code: 200,
      message: "ok",
      data: [{ id: 1, name: "要闻" }],
    });

    await expect(fetchNewsCategories()).resolves.toEqual([
      { id: 1, name: "要闻" },
    ]);
  });

  it("throws when envelope code is not 200", async () => {
    mockFetchResponse({
      code: 500,
      message: "列表失败",
      data: null,
    });

    await expect(fetchNewsCategories()).rejects.toMatchObject({
      message: "列表失败",
      code: 500,
    });
  });

  it("throws for http failures", async () => {
    mockFetchResponse(
      {
        code: 500,
        message: "服务崩了",
        data: null,
      },
      500,
    );

    await expect(fetchNewsCategories()).rejects.toMatchObject({
      message: "服务崩了",
      status: 500,
    });
  });

  it("normalizes 429 errors into a fixed message", async () => {
    mockFetchResponse(
      {
        code: 429,
        message: "rate limited",
        data: null,
      },
      429,
    );

    await expect(fetchNewsList(1, 1)).rejects.toMatchObject({
      message: "请求过于频繁，请稍后再试",
      status: 429,
      code: 429,
    });
  });

  it("parses raw chat responses", async () => {
    mockFetchResponse({
      answer: "整理后的答案",
      loop_count: 2,
      news_list: [
        {
          id: 9,
          title: "芯片供应链",
          content: "完整内容",
          category_id: 7,
          publish_time: "2026-04-22T09:00:00",
        },
      ],
    });

    await expect(fetchChatResult("芯片")).resolves.toEqual({
      answer: "整理后的答案",
      loopCount: 2,
      newsList: [
        {
          id: 9,
          title: "芯片供应链",
          description: "完整内容",
          image: null,
          author: null,
          categoryId: 7,
          views: 0,
          publishTime: "2026-04-22T09:00:00",
        },
      ],
    });
  });

  it("maps mixed field naming into a stable news list model", async () => {
    mockFetchResponse({
      code: 200,
      message: "ok",
      data: {
        list: [
          {
            id: 3,
            title: "夜间快报",
            description: "摘要",
            category_id: 2,
            publishedTime: "2026-04-22T10:00:00",
            views: "12",
          },
        ],
        total: 1,
        has_more: true,
      },
    });

    await expect(fetchNewsList(2, 1)).resolves.toEqual({
      list: [
        {
          id: 3,
          title: "夜间快报",
          description: "摘要",
          image: null,
          author: null,
          categoryId: 2,
          views: 12,
          publishTime: "2026-04-22T10:00:00",
        },
      ],
      total: 1,
      hasMore: true,
    });
  });
});
