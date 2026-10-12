"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BarChart3,
  BookOpen,
  Bot,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Settings,
  Ticket,
  Users,
} from "lucide-react";
import { useAuth } from "@/components/auth/auth-provider";
import { BrandMark } from "@/components/ui/brand-mark";
import { cn } from "@/lib/utils";

const mainNav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/customers", label: "Customers", icon: Users },
  { href: "/dashboard/conversations", label: "Conversations", icon: MessageSquare },
  { href: "/dashboard/tickets", label: "Tickets", icon: Ticket },
  { href: "/dashboard/knowledge", label: "Knowledge Base", icon: BookOpen },
];

const aiNav = [
  { href: "/dashboard/agents", label: "Agent Activity", icon: Bot },
  { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
];

const systemNav = [
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

function NavSection({
  title,
  items,
}: {
  title: string;
  items: typeof mainNav;
}) {
  const pathname = usePathname();

  return (
    <div className="mb-5">
      <p className="mb-1.5 px-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted/80">
        {title}
      </p>
      <nav className="space-y-0.5">
        {items.map((item) => {
          const active =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(item.href);
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-accent-soft text-accent"
                  : "text-muted hover:bg-canvas hover:text-ink"
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

function roleLabel(role: string) {
  if (role === "support_agent") return "Support Agent";
  if (role === "admin") return "Admin";
  return role;
}

function initials(name: string) {
  return (
    name
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("") || "U"
  );
}

export function DashboardSidebar() {
  const { user, logout } = useAuth();
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <aside className="flex h-full w-60 flex-col border-r border-line bg-surface">
      <div className="flex h-14 items-center border-b border-line px-4">
        <BrandMark />
      </div>

      <div className="flex-1 overflow-y-auto px-2.5 py-4">
        <NavSection title="Main" items={mainNav} />
        <NavSection title="AI" items={aiNav} />
        <NavSection title="System" items={systemNav} />
      </div>

      <div className="border-t border-line p-3">
        <Link
          href="/profile"
          className="flex items-center gap-2.5 rounded-lg p-1.5 transition hover:bg-canvas"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand text-xs font-semibold text-white">
            {user ? initials(user.name) : "—"}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-ink">
              {user?.name ?? "User"}
            </p>
            <p className="truncate text-[11px] text-muted">
              {user ? roleLabel(user.role) : ""}
            </p>
          </div>
        </Link>
        <button
          type="button"
          onClick={() => void handleLogout()}
          className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg border border-line px-3 py-1.5 text-sm font-medium text-ink transition hover:bg-canvas"
        >
          <LogOut className="h-3.5 w-3.5" />
          Logout
        </button>
      </div>
    </aside>
  );
}
