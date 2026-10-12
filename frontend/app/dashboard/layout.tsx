"use client";

import { useState } from "react";
import { RequireStaff } from "@/components/auth/route-guards";
import { DashboardHeader } from "@/components/dashboard/dashboard-header";
import { DashboardSidebar } from "@/components/dashboard/dashboard-sidebar";
import { cn } from "@/lib/utils";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <RequireStaff>
      <div className="flex h-screen overflow-hidden bg-canvas">
        <div className="hidden lg:block">
          <DashboardSidebar />
        </div>

        {sidebarOpen ? (
          <div className="fixed inset-0 z-50 lg:hidden">
            <button
              type="button"
              className="absolute inset-0 bg-black/40"
              aria-label="Close sidebar"
              onClick={() => setSidebarOpen(false)}
            />
            <div className="relative h-full w-64 shadow-xl">
              <DashboardSidebar />
            </div>
          </div>
        ) : null}

        <div className="flex min-w-0 flex-1 flex-col">
          <DashboardHeader onMenuClick={() => setSidebarOpen(true)} />
          <main className={cn("flex-1 overflow-y-auto")}>{children}</main>
        </div>
      </div>
    </RequireStaff>
  );
}
