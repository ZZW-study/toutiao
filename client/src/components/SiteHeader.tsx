import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "新闻首页" },
  { to: "/ask", label: "AI 问答" },
];

export function SiteHeader() {
  return (
    <header className="site-header">
      <div className="site-header__inner">
        <NavLink to="/" className="brand-mark">
          <span className="brand-mark__prefix">TT</span>
          <span className="brand-mark__body">
            <strong>头条编辑台</strong>
            <small>Desktop News Desk</small>
          </span>
        </NavLink>

        <nav className="site-nav" aria-label="主导航">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                isActive
                  ? "site-nav__link is-active"
                  : "site-nav__link"
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <p className="site-header__meta">
          每次打开，先看重点，再读全文。
        </p>
      </div>
    </header>
  );
}
