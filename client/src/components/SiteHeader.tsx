import { startTransition, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../features/auth/useAuth";

export function SiteHeader() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, openAuthModal, user } = useAuth();
  const currentQuery = new URLSearchParams(location.search).get("q") ?? "";
  const [draft, setDraft] = useState(currentQuery);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const nextQuery = draft.trim();

    startTransition(() => {
      navigate(
        nextQuery
          ? `/ask?q=${encodeURIComponent(nextQuery)}`
          : "/ask",
      );
    });
  };

  return (
    <header className="site-header">
      <div className="site-header__inner">
        <Link to="/" className="brand-lockup">
          <span className="brand-lockup__mark">头条</span>
          <span className="brand-lockup__text">
            <strong>今日头条</strong>
            <small>桌面资讯站</small>
          </span>
        </Link>

        <form className="site-search" onSubmit={handleSubmit}>
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="搜索新闻主题，或直接发起 AI 问答"
          />
          <button type="submit">搜索</button>
        </form>

        <div className="site-header__actions">
          <Link to="/ask" className="site-header__action-link">
            AI 问答
          </Link>
          {isAuthenticated && user ? (
            <Link to="/profile" className="site-header__profile">
              {user.nickname ?? user.username}
            </Link>
          ) : (
            <button
              type="button"
              className="site-header__auth-button"
              onClick={() => openAuthModal("login")}
            >
              登录 / 注册
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
