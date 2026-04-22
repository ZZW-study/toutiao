import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { jsonResponse } from "../../test/http";
import { renderApp } from "../../test/renderApp";

function installShellApi() {
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

      if (url.pathname === "/api/news/list") {
        return jsonResponse({
          code: 200,
          message: "ok",
          data: {
            list: [
              {
                id: 1,
                title: "首页新闻",
                description: "首页摘要",
                categoryId: 1,
                views: 5,
              },
            ],
            total: 1,
            hasMore: false,
          },
        });
      }

      if (url.pathname === "/api/user/login") {
        return jsonResponse({
          code: 200,
          message: "ok",
          data: {
            token: "token-1",
            userInfo: {
              id: 9,
              username: "reader",
              nickname: "读者",
              avatar: null,
              gender: null,
              bio: null,
              phone: null,
            },
          },
        });
      }

      throw new Error(`Unhandled URL: ${url.toString()}`);
    }),
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("auth flow", () => {
  it("opens the auth modal when a protected nav item is clicked", async () => {
    installShellApi();
    const user = userEvent.setup();

    renderApp(["/"]);

    await screen.findByRole("heading", { name: "首页新闻" });
    await user.click(screen.getByRole("link", { name: "我的收藏" }));

    expect(
      await screen.findByRole("heading", {
        name: "登录后同步收藏与历史",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("我的收藏 需要登录后查看")).toBeInTheDocument();
  });

  it("logs in from the modal and updates the shell identity block", async () => {
    installShellApi();
    const user = userEvent.setup();

    renderApp(["/"]);

    await screen.findByRole("heading", { name: "首页新闻" });
    await user.click(screen.getByRole("button", { name: "登录 / 注册" }));
    await user.type(screen.getByLabelText("用户名"), "reader");
    await user.type(screen.getByLabelText("密码"), "pass123");
    const dialog = screen.getByRole("dialog");
    const submitButton = dialog.querySelector(
      ".auth-form__submit",
    ) as HTMLButtonElement | null;
    expect(submitButton).not.toBeNull();
    await user.click(submitButton as HTMLButtonElement);

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    expect(
      screen.getByRole("link", { name: "读者" }),
    ).toBeInTheDocument();
    expect(screen.getByText("@reader")).toBeInTheDocument();
  });
});
