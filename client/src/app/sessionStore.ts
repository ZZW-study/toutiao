import type { UserInfo } from "../api/types";

const STORAGE_KEY = "toutiao-client-session";

export interface StoredSession {
  token: string;
  user: UserInfo | null;
}

type SessionListener = (session: StoredSession | null) => void;

const listeners = new Set<SessionListener>();

function readFromStorage() {
  if (typeof window === "undefined") {
    return null;
  }

  const rawValue = window.localStorage.getItem(STORAGE_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    const parsedValue = JSON.parse(rawValue) as StoredSession;
    if (
      typeof parsedValue?.token === "string" &&
      parsedValue.token.trim()
    ) {
      return {
        token: parsedValue.token,
        user: parsedValue.user ?? null,
      } satisfies StoredSession;
    }
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
  }

  return null;
}

let currentSession = readFromStorage();

function notify() {
  listeners.forEach((listener) => listener(currentSession));
}

export function getStoredSession() {
  return currentSession;
}

export function setStoredSession(session: StoredSession | null) {
  currentSession = session;

  if (typeof window !== "undefined") {
    if (session) {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(session),
      );
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }

  notify();
}

export function updateStoredUser(user: UserInfo | null) {
  if (!currentSession) {
    return;
  }

  setStoredSession({
    ...currentSession,
    user,
  });
}

export function subscribeStoredSession(listener: SessionListener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
