import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { jsonResponse } from "../../test/http";
import { renderApp } from "../../test/renderApp";

const session = {
  token: "token-9",
  user: {
    id: 9,
    username: "reader",
    nickname: "读者",
    avatar: null,
    gender: null,
    bio: "原简介",
    phone: "13800000000",
  },
};

function installProtectedApi(
  extraHandler: (url: URL) => Promise<Response> | Response,
) {
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

      if (url.pathname === "/api/user/info") {
        return jsonResponse({
          code: 200,
          message: "ok",
          data: session.user,
        });
      }

      if (url.pathname === "/api/favorite/check") {
        return jsonResponse({
          code: 200,
          message: "ok",
          data: { isFavorite: true },
        });
      }

      return extraHandler(url);
    }),
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("protected pages", () => {
  it("renders favorites and clears them through the backend api", async () => {
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
          data: session.user,
        });
      }

      if (url.pathname === "/api/favorite/check") {
        return jsonResponse({
          code: 200,
          message: "ok",
          data: { isFavorite: true },
        });
      }

      if (url.pathname === "/api/favorite/list") {
        return jsonResponse({
          code: 200,
          message: "ok",
          data: {
            list: [
              {
                id: 7,
                title: "收藏报道",
                description: "收藏摘要",
                categoryId: 1,
                favoriteId: 17,
                favoriteTime: "2026-04-22T10:00:00",
                views: 80,
              },
            ],
            total: 1,
            hasMore: false,
          },
        });
      }

      if (url.pathname === "/api/favorite/clear") {
        return jsonResponse({
          code: 200,
          message: "ok",
          data: null,
        });
      }

      throw new Error(`Unhandled URL: ${url.toString()}`);
    });

    vi.stubGlobal("fetch", fetchSpy);

    const user = userEvent.setup();
    renderApp(["/favorites"], { session });

    expect(await screen.findByText("收藏报道")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "清空收藏" }));

    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.some((call) =>
          String(call[0]).includes("/api/favorite/clear"),
        ),
      ).toBe(true);
    });
  });

  it("renders history entries and deletes a single record", async () => {
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
          data: session.user,
        });
      }

      if (url.pathname === "/api/favorite/check") {
        return jsonResponse({
          code: 200,
          message: "ok",
          data: { isFavorite: false },
        });
      }

      if (url.pathname === "/api/history/list") {
        return jsonResponse({
          code: 200,
          message: "ok",
          data: {
            list: [
              {
                id: 5,
                historyId: 7,
                title: "历史报道",
                description: "历史摘要",
                categoryId: 1,
                viewTime: "2026-04-22T11:00:00",
                views: 100,
              },
            ],
            total: 1,
            hasMore: false,
          },
        });
      }

      if (url.pathname === "/api/history/delete/7") {
        return jsonResponse({
          code: 200,
          message: "ok",
          data: null,
        });
      }

      throw new Error(`Unhandled URL: ${url.toString()}`);
    });

    vi.stubGlobal("fetch", fetchSpy);

    const user = userEvent.setup();
    renderApp(["/history"], { session });

    expect(await screen.findByText("历史报道")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "删除记录" }));

    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.some((call) =>
          String(call[0]).includes("/api/history/delete/7"),
        ),
      ).toBe(true);
    });
  });

  it("updates profile info and password from the profile page", async () => {
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
          data: session.user,
        });
      }

      if (url.pathname === "/api/user/update") {
        return jsonResponse({
          code: 200,
          message: "ok",
          data: {
            ...session.user,
            nickname: "新昵称",
          },
        });
      }

      if (url.pathname === "/api/user/password") {
        return jsonResponse({
          code: 200,
          message: "ok",
          data: null,
        });
      }

      throw new Error(`Unhandled URL: ${url.toString()}`);
    });

    vi.stubGlobal("fetch", fetchSpy);

    const user = userEvent.setup();
    renderApp(["/profile"], { session });

    const nicknameInput = await screen.findByDisplayValue("读者");
    await user.clear(nicknameInput);
    await user.type(nicknameInput, "新昵称");
    await user.click(screen.getByRole("button", { name: "保存资料" }));

    expect(await screen.findByText("资料已更新")).toBeInTheDocument();

    await user.type(screen.getByLabelText("旧密码"), "old-pass");
    await user.type(screen.getByLabelText("新密码"), "new-pass");
    await user.click(screen.getByRole("button", { name: "更新密码" }));

    expect(await screen.findByText("密码修改成功")).toBeInTheDocument();
    expect(
      fetchSpy.mock.calls.some((call) =>
        String(call[0]).includes("/api/user/update"),
      ),
    ).toBe(true);
    expect(
      fetchSpy.mock.calls.some((call) =>
        String(call[0]).includes("/api/user/password"),
      ),
    ).toBe(true);
  });
});
