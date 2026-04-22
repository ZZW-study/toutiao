import { getStoredSession, setStoredSession } from "../app/sessionStore";
import { ApiError } from "./errors";
import type { ApiEnvelope } from "./types";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

export interface RequestOptions {
  auth?: "include" | "omit";
}

function buildUrl(path: string) {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

function buildHeaders(
  headers?: HeadersInit,
  options?: RequestOptions,
) {
  const nextHeaders = new Headers(headers);
  nextHeaders.set("Accept", "application/json");

  if (!nextHeaders.has("Content-Type")) {
    nextHeaders.set("Content-Type", "application/json");
  }

  if (options?.auth !== "omit") {
    const token = getStoredSession()?.token;
    if (token && !nextHeaders.has("Authorization")) {
      nextHeaders.set("Authorization", `Bearer ${token}`);
    }
  }

  return nextHeaders;
}

async function readJson(response: Response) {
  const rawText = await response.text();
  if (!rawText) {
    return null;
  }

  try {
    return JSON.parse(rawText) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function resolveMessage(
  status: number,
  payload: Record<string, unknown> | null,
) {
  if (status === 429 || payload?.code === 429) {
    return "请求过于频繁，请稍后重试";
  }

  if (typeof payload?.message === "string" && payload.message.trim()) {
    return payload.message;
  }

  if (typeof payload?.detail === "string" && payload.detail.trim()) {
    return payload.detail;
  }

  if (status === 401) {
    return "登录状态已失效，请重新登录";
  }

  if (status >= 500) {
    return "服务暂时不可用，请稍后重试";
  }

  return "请求失败，请稍后重试";
}

function toApiError(
  status: number,
  payload: Record<string, unknown> | null,
) {
  const code = typeof payload?.code === "number" ? payload.code : status;
  return new ApiError(status, code, resolveMessage(status, payload));
}

async function requestJson(
  path: string,
  init?: RequestInit,
  options?: RequestOptions,
) {
  const response = await fetch(buildUrl(path), {
    ...init,
    headers: buildHeaders(init?.headers, options),
  });
  const payload = await readJson(response);

  if (!response.ok) {
    if (response.status === 401 && options?.auth !== "omit") {
      setStoredSession(null);
    }

    throw toApiError(response.status, payload);
  }

  return payload;
}

export async function requestEnvelope<T>(
  path: string,
  init?: RequestInit,
  options?: RequestOptions,
) {
  const payload = await requestJson(path, init, options);

  if (
    !payload ||
    typeof payload.code !== "number" ||
    !("data" in payload)
  ) {
    throw new ApiError(
      500,
      500,
      "响应格式不符合预期",
    );
  }

  if (payload.code !== 200) {
    throw toApiError(payload.code, payload);
  }

  const envelope = payload as unknown as ApiEnvelope<T>;
  return envelope.data;
}

export async function requestRaw<T>(
  path: string,
  init?: RequestInit,
  options?: RequestOptions,
) {
  const payload = await requestJson(path, init, options);

  if (!payload || typeof payload !== "object") {
    throw new ApiError(
      500,
      500,
      "响应格式不符合预期",
    );
  }

  return payload as T;
}
