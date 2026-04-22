import { useEffect, useState } from "react";

import { getErrorMessage } from "../../api/errors";
import { useAuth } from "./useAuth";

export function AuthModal() {
  const {
    authMode,
    authReason,
    closeAuthModal,
    isAuthModalOpen,
    login,
    register,
    setAuthMode,
  } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(
    null,
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!isAuthModalOpen) {
      setUsername("");
      setPassword("");
      setConfirmPassword("");
      setErrorMessage(null);
      setIsSubmitting(false);
    }
  }, [isAuthModalOpen, authMode]);

  if (!isAuthModalOpen) {
    return null;
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!username.trim() || !password.trim()) {
      setErrorMessage("请输入用户名和密码");
      return;
    }

    if (authMode === "register" && password !== confirmPassword) {
      setErrorMessage("两次输入的密码不一致");
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      if (authMode === "login") {
        await login(username.trim(), password);
      } else {
        await register(username.trim(), password);
      }
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="auth-modal"
      role="presentation"
      onClick={closeAuthModal}
    >
      <div
        className="auth-modal__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <button
          type="button"
          className="auth-modal__close"
          onClick={closeAuthModal}
          aria-label="关闭登录弹层"
        >
          ×
        </button>

        <div className="auth-modal__tabs">
          <button
            type="button"
            className={
              authMode === "login"
                ? "auth-modal__tab is-active"
                : "auth-modal__tab"
            }
            onClick={() => setAuthMode("login")}
          >
            登录
          </button>
          <button
            type="button"
            className={
              authMode === "register"
                ? "auth-modal__tab is-active"
                : "auth-modal__tab"
            }
            onClick={() => setAuthMode("register")}
          >
            注册
          </button>
        </div>

        <div className="auth-modal__copy">
          <p className="eyebrow">Account Center</p>
          <h2 id="auth-modal-title">
            {authMode === "login" ? "登录后同步收藏与历史" : "创建账号开始追踪内容"}
          </h2>
          <p>
            {authReason ??
              "登录后即可保存新闻、管理浏览记录，并在个人中心维护资料。"}
          </p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="auth-form__field">
            <span>用户名</span>
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="输入用户名"
            />
          </label>

          <label className="auth-form__field">
            <span>密码</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="输入密码"
            />
          </label>

          {authMode === "register" ? (
            <label className="auth-form__field">
              <span>确认密码</span>
              <input
                type="password"
                value={confirmPassword}
                onChange={(event) =>
                  setConfirmPassword(event.target.value)
                }
                placeholder="再次输入密码"
              />
            </label>
          ) : null}

          {errorMessage ? (
            <p className="auth-form__error">{errorMessage}</p>
          ) : null}

          <button
            type="submit"
            className="auth-form__submit"
            disabled={isSubmitting}
          >
            {isSubmitting
              ? "提交中..."
              : authMode === "login"
                ? "登录"
                : "注册并登录"}
          </button>
        </form>
      </div>
    </div>
  );
}
