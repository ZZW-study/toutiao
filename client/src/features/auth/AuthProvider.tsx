import {
  createContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  fetchCurrentUser,
  login as loginRequest,
  register as registerRequest,
} from "../../api/user";
import type {
  AuthSession,
  UserInfo,
} from "../../api/types";
import {
  getStoredSession,
  setStoredSession,
  subscribeStoredSession,
  updateStoredUser,
  type StoredSession,
} from "../../app/sessionStore";
import { AuthModal } from "./AuthModal";

type AuthMode = "login" | "register";

interface AuthContextValue {
  authMode: AuthMode;
  authReason: string | null;
  closeAuthModal: () => void;
  isAuthenticated: boolean;
  isAuthModalOpen: boolean;
  isRefreshingUser: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  openAuthModal: (mode?: AuthMode, reason?: string) => void;
  register: (username: string, password: string) => Promise<void>;
  requireAuth: (reason?: string) => boolean;
  setAuthMode: (mode: AuthMode) => void;
  syncUser: (user: UserInfo) => void;
  token: string | null;
  user: UserInfo | null;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

function getProtectedQueryRoots() {
  return new Set([
    "auth-user",
    "favorite-check",
    "favorite-list",
    "history-list",
  ]);
}

export function AuthProvider({
  children,
}: {
  children: ReactNode;
}) {
  const queryClient = useQueryClient();
  const [session, setSession] = useState<StoredSession | null>(
    () => getStoredSession(),
  );
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [authReason, setAuthReason] = useState<string | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  const token = session?.token ?? null;
  const userQuery = useQuery({
    queryKey: ["auth-user", token],
    queryFn: fetchCurrentUser,
    enabled: Boolean(token),
    initialData: session?.user ?? undefined,
    retry: false,
  });

  useEffect(() => {
    return subscribeStoredSession((nextSession) => {
      setSession(nextSession);
    });
  }, []);

  useEffect(() => {
    if (userQuery.data && token) {
      updateStoredUser(userQuery.data);
    }
  }, [token, userQuery.data]);

  const closeAuthModal = () => {
    setIsAuthModalOpen(false);
    setAuthReason(null);
  };

  const openAuthModal = (
    mode: AuthMode = "login",
    reason?: string,
  ) => {
    setAuthMode(mode);
    setAuthReason(reason ?? null);
    setIsAuthModalOpen(true);
  };

  const syncUser = (user: UserInfo) => {
    updateStoredUser(user);

    if (token) {
      queryClient.setQueryData(["auth-user", token], user);
    }
  };

  const commitSession = (nextSession: AuthSession) => {
    setStoredSession({
      token: nextSession.token,
      user: nextSession.userInfo,
    });
    queryClient.setQueryData(
      ["auth-user", nextSession.token],
      nextSession.userInfo,
    );
  };

  const login = async (username: string, password: string) => {
    const nextSession = await loginRequest(username, password);
    commitSession(nextSession);
    closeAuthModal();
  };

  const register = async (username: string, password: string) => {
    const nextSession = await registerRequest(username, password);
    commitSession(nextSession);
    closeAuthModal();
  };

  const logout = () => {
    setStoredSession(null);
    closeAuthModal();
    const protectedRoots = getProtectedQueryRoots();
    queryClient.removeQueries({
      predicate: (query) =>
        protectedRoots.has(String(query.queryKey[0] ?? "")),
    });
  };

  const requireAuth = (reason?: string) => {
    if (token) {
      return true;
    }

    openAuthModal("login", reason);
    return false;
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      authMode,
      authReason,
      closeAuthModal,
      isAuthenticated: Boolean(token),
      isAuthModalOpen,
      isRefreshingUser: Boolean(token) && userQuery.isFetching,
      login,
      logout,
      openAuthModal,
      register,
      requireAuth,
      setAuthMode,
      syncUser,
      token,
      user: userQuery.data ?? session?.user ?? null,
    }),
    [
      authMode,
      authReason,
      isAuthModalOpen,
      session?.user,
      token,
      userQuery.data,
      userQuery.isFetching,
    ],
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
      <AuthModal />
    </AuthContext.Provider>
  );
}
