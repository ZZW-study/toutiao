import {
  mapAuthSession,
  mapUserInfo,
} from "./mappers";
import {
  requestEnvelope,
  type RequestOptions,
} from "./client";
import type {
  AuthSession,
  ChangePasswordPayload,
  UpdateUserPayload,
  UserInfo,
} from "./types";

const AUTH_DISABLED: RequestOptions = { auth: "omit" };

export async function login(
  username: string,
  password: string,
) {
  const rawData = await requestEnvelope<unknown>(
    "/api/user/login",
    {
      method: "POST",
      body: JSON.stringify({ username, password }),
    },
    AUTH_DISABLED,
  );

  return mapAuthSession(rawData) as AuthSession;
}

export async function register(
  username: string,
  password: string,
) {
  const rawData = await requestEnvelope<unknown>(
    "/api/user/register",
    {
      method: "POST",
      body: JSON.stringify({ username, password }),
    },
    AUTH_DISABLED,
  );

  return mapAuthSession(rawData) as AuthSession;
}

export async function fetchCurrentUser() {
  const rawData = await requestEnvelope<unknown>("/api/user/info");
  return mapUserInfo(rawData) as UserInfo;
}

export async function updateUserProfile(
  payload: UpdateUserPayload,
) {
  const rawData = await requestEnvelope<unknown>(
    "/api/user/update",
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
  );

  return mapUserInfo(rawData) as UserInfo;
}

export async function changePassword(
  payload: ChangePasswordPayload,
) {
  return requestEnvelope(
    "/api/user/password",
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
  );
}
