import { Link, NavLink, useLocation } from "react-router-dom";

import { useCategories } from "../features/news/hooks";
import { useAuth } from "../features/auth/useAuth";

const primaryLinks = [
  { to: "/", label: "推荐", protected: false },
  { to: "/ask", label: "AI 问答", protected: false },
  { to: "/favorites", label: "我的收藏", protected: true },
  { to: "/history", label: "浏览历史", protected: true },
  { to: "/profile", label: "个人中心", protected: true },
];

export function MainSidebar() {
  const categoriesQuery = useCategories();
  const { isAuthenticated, openAuthModal } = useAuth();
  const location = useLocation();
  const currentCategoryId = Number(
    new URLSearchParams(location.search).get("category") ?? 0,
  );

  return (
    <aside className="shell-sidebar">
      <div className="sidebar-panel">
        <p className="sidebar-panel__label">主导航</p>
        <nav className="sidebar-nav">
          {primaryLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                isActive
                  ? "sidebar-nav__item is-active"
                  : "sidebar-nav__item"
              }
              onClick={(event) => {
                if (!link.protected || isAuthenticated) {
                  return;
                }

                event.preventDefault();
                openAuthModal("login", `${link.label} 需要登录后查看`);
              }}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="sidebar-panel">
        <p className="sidebar-panel__label">频道</p>
        {categoriesQuery.isLoading ? (
          <p className="sidebar-panel__hint">加载频道中...</p>
        ) : categoriesQuery.data?.length ? (
          <div className="sidebar-channel-list">
            {categoriesQuery.data.map((category) => (
              <Link
                key={category.id}
                to={`/?category=${category.id}&page=1`}
                className={
                  currentCategoryId === category.id &&
                  location.pathname === "/"
                    ? "sidebar-channel is-active"
                    : "sidebar-channel"
                }
              >
                {category.name}
              </Link>
            ))}
          </div>
        ) : (
          <p className="sidebar-panel__hint">暂无频道数据</p>
        )}
      </div>
    </aside>
  );
}
