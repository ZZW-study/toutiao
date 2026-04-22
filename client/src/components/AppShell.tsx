import { Outlet } from "react-router-dom";

import { SiteHeader } from "./SiteHeader";

export function AppShell() {
  return (
    <div className="app-shell">
      <SiteHeader />
      <main className="page-shell">
        <Outlet />
      </main>
      <footer className="site-footer">
        <div className="site-footer__inner">
          <p>头条编辑台</p>
          <span>分类浏览、深度阅读、AI 追问</span>
        </div>
      </footer>
    </div>
  );
}
