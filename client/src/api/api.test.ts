import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchChatResult } from "./chat";
import { fetchFavorites } from "./favorite";
import { fetchHistory } from "./history";
import { fetchNewsCategories, fetchNewsList } from "./news";
import { login } from "./user";
import { setStoredSession, getStoredSession } from "../app/sessionStore";

function mockFetchResponse(body: unknown, status = 200) {
  const fetchSpy = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: {
        "Content-Type": "application/json",
      },
    }),
  );

  vi.stubGlobal("fetch", fetchSpy);
  return fetchSpy;
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  setStoredSession(null);
});

describe("api adapters", () => {
  it("parses envelope success responses", async () => {
    mockFetchResponse({
      code: 200,
      message: "ok",
      data: [{ id: 1, name: "推荐" }],
    });

    await expect(fetchNewsCategories()).resolves.toEqual([
      { id: 1, name: "推荐" },
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
      message: "请求过于频繁，请稍后重试",
      status: 429,
      code: 429,
    });
  });

  it("parses raw chat responses", async () => {
    mockFetchResponse({
      answer: "这是整理后的答案",
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
      answer: "这是整理后的答案",
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

  it("injects bearer tokens for authenticated favorite requests", async () => {
    setStoredSession({
      token: "token-123",
      user: null,
    });

    const fetchSpy = mockFetchResponse({
      code: 200,
      message: "ok",
      data: {
        list: [],
        total: 0,
        hasMore: false,
      },
    });

    await fetchFavorites(1);

    const headers = new Headers(fetchSpy.mock.calls[0]?.[1]?.headers);
    expect(headers.get("Authorization")).toBe("Bearer token-123");
  });

  it("maps favorite and history lists with mixed field naming", async () => {
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
            favorite_id: 5,
            favorite_time: "2026-04-22T10:10:00",
            historyId: 7,
            viewTime: "2026-04-22T10:20:00",
            views: "12",
          },
        ],
        total: 1,
        has_more: true,
      },
    });

    await expect(fetchFavorites(1)).resolves.toEqual({
      list: [
        {
          id: 3,
          title: "夜间快报",
          description: "摘要",
          image: null,
          author: null,
          categoryId: 2,
          favoriteId: 5,
          favoriteTime: "2026-04-22T10:10:00",
          publishTime: "2026-04-22T10:00:00",
          views: 12,
        },
      ],
      total: 1,
      hasMore: true,
    });

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
            history_id: 7,
            view_time: "2026-04-22T10:20:00",
            views: "12",
          },
        ],
        total: 1,
        hasMore: true,
      },
    });

    await expect(fetchHistory(1)).resolves.toEqual({
      list: [
        {
          id: 3,
          title: "夜间快报",
          description: "摘要",
          image: null,
          author: null,
          categoryId: 2,
          historyId: 7,
          publishTime: "2026-04-22T10:00:00",
          viewTime: "2026-04-22T10:20:00",
          views: 12,
        },
      ],
      total: 1,
      hasMore: true,
    });
  });

  it("omits auth headers for login and keeps the current session on login failures", async () => {
    setStoredSession({
      token: "still-valid",
      user: {
        id: 1,
        username: "reader",
        nickname: "Reader",
        avatar: null,
        gender: null,
        bio: null,
        phone: null,
      },
    });

    const fetchSpy = mockFetchResponse(
      {
        detail: "输入密码错误，请重试",
      },
      401,
    );

    await expect(login("reader", "bad-pass")).rejects.toMatchObject({
      message: "输入密码错误，请重试",
      status: 401,
    });

    const headers = new Headers(fetchSpy.mock.calls[0]?.[1]?.headers);
    expect(headers.get("Authorization")).toBeNull();
    expect(getStoredSession()?.token).toBe("still-valid");
  });
});
