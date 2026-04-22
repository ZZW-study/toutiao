import { Outlet } from "react-router-dom";

import { MainSidebar } from "./MainSidebar";
import { RightRail } from "./RightRail";
import { SiteHeader } from "./SiteHeader";

export function AppShell() {
  return (
    <div className="app-shell">
      <SiteHeader />
      <div className="shell-layout">
        <MainSidebar />
        <main className="shell-main">
          <Outlet />
        </main>
        <RightRail />
      </div>
    </div>
  );
}
