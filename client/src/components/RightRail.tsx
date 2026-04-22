import { Link } from "react-router-dom";

import { useAuth } from "../features/auth/useAuth";

export function RightRail() {
  const {
    isAuthenticated,
    logout,
    openAuthModal,
    user,
  } = useAuth();

  const handleProtectedClick = (
    event: React.MouseEvent<HTMLAnchorElement>,
    label: string,
  ) => {
    if (isAuthenticated) {
      return;
    }

    event.preventDefault();
    openAuthModal("login", `${label} 需要登录后查看`);
  };

  return (
    <aside className="right-rail">
      <section className="rail-card rail-card--account">
        <p className="eyebrow">Account</p>
        {isAuthenticated && user ? (
          <>
            <div className="user-chip">
              <div className="user-chip__avatar">
                {user.avatar ? (
                  <img src={user.avatar} alt={user.username} />
                ) : (
                  <span>{user.username.slice(0, 1).toUpperCase()}</span>
                )}
              </div>
              <div className="user-chip__body">
                <strong>{user.nickname ?? user.username}</strong>
                <span>@{user.username}</span>
              </div>
            </div>

            <div className="rail-actions">
              <Link to="/profile" className="button button--primary">
                编辑资料
              </Link>
              <button
                type="button"
                className="button button--ghost"
                onClick={logout}
              >
                退出登录
              </button>
            </div>
          </>
        ) : (
          <>
            <h3 className="rail-card__title">登录后同步收藏与阅读足迹</h3>
            <p className="rail-card__body">
              在同一账号下管理收藏、浏览历史和个人资料，右侧功能区会自动联动更新。
            </p>
            <div className="rail-actions">
              <button
                type="button"
                className="button button--primary"
                onClick={() => openAuthModal("login")}
              >
                登录
              </button>
              <button
                type="button"
                className="button button--ghost"
                onClick={() => openAuthModal("register")}
              >
                注册
              </button>
            </div>
          </>
        )}
      </section>

      <section className="rail-card">
        <p className="eyebrow">Quick Access</p>
        <div className="quick-link-list">
          <Link to="/ask" className="quick-link">
            AI 问答台
          </Link>
          <Link
            to="/favorites"
            className="quick-link"
            onClick={(event) =>
              handleProtectedClick(event, "收藏夹")
            }
          >
            收藏夹
          </Link>
          <Link
            to="/history"
            className="quick-link"
            onClick={(event) =>
              handleProtectedClick(event, "浏览历史")
            }
          >
            浏览历史
          </Link>
        </div>
      </section>

      <section className="rail-card">
        <p className="eyebrow">Today</p>
        <h3 className="rail-card__title">把热点浏览、问答和个人同步放在同一工作区里。</h3>
        <p className="rail-card__body">
          首页负责刷流，详情负责阅读，问答负责总结，右侧区域负责登录态和快捷操作。
        </p>
      </section>
    </aside>
  );
}
