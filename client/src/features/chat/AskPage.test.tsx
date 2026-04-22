import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { jsonResponse } from "../../test/http";
import { renderApp } from "../../test/renderApp";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("AskPage", () => {
  it("submits a query, syncs it into the url, and renders the answer", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string | URL) => {
        const url = new URL(String(input));

        if (url.pathname === "/chat/") {
          return jsonResponse({
            answer: "这是答案",
            loop_count: 1,
            news_list: [
              {
                id: 6,
                title: "芯片追踪",
                content: "补充内容",
                category_id: 7,
                publish_time: "2026-04-22T13:00:00",
              },
            ],
          });
        }

        throw new Error(`Unhandled URL: ${url.toString()}`);
      }),
    );

    const user = userEvent.setup();
    renderApp(["/ask"]);

    await user.type(
      screen.getByLabelText("输入新闻问题"),
      "半导体",
    );
    await user.click(screen.getByRole("button", { name: "开始追问" }));

    await waitFor(() => {
      expect(screen.getByTestId("location-probe")).toHaveTextContent(
        "/ask?q=%E5%8D%8A%E5%AF%BC%E4%BD%93",
      );
    });

    expect(await screen.findByText("这是答案")).toBeInTheDocument();
    expect(screen.getByText("芯片追踪")).toBeInTheDocument();
  });

  it("shows an error message and allows retrying the same question", async () => {
    let attempts = 0;

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string | URL) => {
        const url = new URL(String(input));

        if (url.pathname !== "/chat/") {
          throw new Error(`Unhandled URL: ${url.toString()}`);
        }

        attempts += 1;
        if (attempts === 1) {
          return jsonResponse(
            {
              code: 500,
              message: "处理失败",
              data: null,
            },
            500,
          );
        }

        return jsonResponse({
          answer: "重试成功",
          loop_count: 1,
          news_list: [],
        });
      }),
    );

    const user = userEvent.setup();
    renderApp(["/ask?q=%E6%B5%8B%E8%AF%95"]);

    expect(
      await screen.findByRole("heading", { name: "问答暂时不可用" }),
    ).toBeInTheDocument();
    expect(screen.getByText("处理失败")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "重试" }));

    expect(await screen.findByText("重试成功")).toBeInTheDocument();
  });
});
