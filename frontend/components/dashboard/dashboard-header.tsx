"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Bell, CheckCheck, LogOut, Menu, Search, UserRound } from "lucide-react";
import { useAuth } from "@/components/auth/auth-provider";
import { Input } from "@/components/ui/input";
import {
  getUnreadNotificationCount,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "@/lib/api";
import type { AppNotification } from "@/lib/types";
import { cn } from "@/lib/utils";

interface DashboardHeaderProps {
  onMenuClick?: () => void;
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

function formatRelativeTime(iso: string | null) {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export function DashboardHeader({ onMenuClick }: DashboardHeaderProps) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifLoading, setNotifLoading] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);

  const refreshNotifications = useCallback(async () => {
    try {
      const [notes, unread] = await Promise.all([
        listNotifications(),
        getUnreadNotificationCount(),
      ]);
      setNotifications(notes);
      setUnreadCount(unread.count);
    } catch {
      // Ignore transient poll errors so the header stays usable.
    }
  }, []);

  useEffect(() => {
    void refreshNotifications();
    const timer = window.setInterval(() => {
      void refreshNotifications();
    }, 8000);
    return () => window.clearInterval(timer);
  }, [refreshNotifications]);

  useEffect(() => {
    function onClickOutside(event: MouseEvent) {
      const target = event.target as Node;
      if (menuRef.current && !menuRef.current.contains(target)) {
        setMenuOpen(false);
      }
      if (notifRef.current && !notifRef.current.contains(target)) {
        setNotifOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  async function openNotifications() {
    const next = !notifOpen;
    setNotifOpen(next);
    setMenuOpen(false);
    if (next) {
      setNotifLoading(true);
      await refreshNotifications();
      setNotifLoading(false);
    }
  }

  async function handleNotificationClick(note: AppNotification) {
    if (!note.isRead) {
      try {
        await markNotificationRead(note.id);
        setNotifications((prev) =>
          prev.map((item) =>
            item.id === note.id ? { ...item, isRead: true } : item
          )
        );
        setUnreadCount((count) => Math.max(0, count - 1));
      } catch {
        // Still navigate even if mark-read fails.
      }
    }
    setNotifOpen(false);
    if (note.conversationId) {
      router.push(`/dashboard/conversations/${note.conversationId}`);
    } else {
      router.push("/dashboard/conversations");
    }
  }

  async function handleMarkAllRead() {
    try {
      await markAllNotificationsRead();
      setNotifications((prev) => prev.map((item) => ({ ...item, isRead: true })));
      setUnreadCount(0);
    } catch {
      // Keep panel open; next poll will resync.
    }
  }

  return (
    <header className="flex h-14 items-center justify-between gap-4 border-b border-line bg-surface px-4 md:px-6">
      <div className="flex flex-1 items-center gap-3">
        <button
          type="button"
          onClick={onMenuClick}
          className="rounded-lg p-2 text-muted hover:bg-canvas lg:hidden"
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="relative w-full max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <Input
            placeholder="Search conversations, tickets..."
            className="h-9 bg-canvas pl-9"
          />
        </div>
      </div>

      <div className="flex items-center gap-1.5">
        <div className="relative" ref={notifRef}>
          <button
            type="button"
            onClick={() => void openNotifications()}
            className="relative rounded-lg p-2 text-muted hover:bg-canvas"
            aria-label="Notifications"
            aria-expanded={notifOpen}
          >
            <Bell className="h-5 w-5" />
            {unreadCount > 0 ? (
              <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[10px] font-semibold leading-none text-white">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            ) : null}
          </button>

          {notifOpen ? (
            <div className="absolute right-0 z-50 mt-2 w-[22rem] max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border border-line bg-surface shadow-lg">
              <div className="flex items-center justify-between border-b border-line px-3 py-2.5">
                <p className="text-sm font-semibold text-ink">Notifications</p>
                {unreadCount > 0 ? (
                  <button
                    type="button"
                    onClick={() => void handleMarkAllRead()}
                    className="inline-flex items-center gap-1 text-xs text-muted hover:text-ink"
                  >
                    <CheckCheck className="h-3.5 w-3.5" />
                    Mark all read
                  </button>
                ) : null}
              </div>

              <div className="max-h-80 overflow-y-auto">
                {notifLoading && notifications.length === 0 ? (
                  <p className="px-3 py-6 text-center text-sm text-muted">
                    Loading…
                  </p>
                ) : notifications.length === 0 ? (
                  <p className="px-3 py-6 text-center text-sm text-muted">
                    No notifications yet.
                  </p>
                ) : (
                  notifications.map((note) => (
                    <button
                      key={note.id}
                      type="button"
                      onClick={() => void handleNotificationClick(note)}
                      className={cn(
                        "flex w-full flex-col gap-0.5 border-b border-line px-3 py-2.5 text-left last:border-b-0 hover:bg-canvas",
                        !note.isRead && "bg-canvas/70"
                      )}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-ink">
                          {note.title}
                        </p>
                        {!note.isRead ? (
                          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                        ) : null}
                      </div>
                      <p className="line-clamp-2 text-xs text-muted">
                        {note.body}
                      </p>
                      <p className="text-[11px] text-muted/80">
                        {formatRelativeTime(note.createdAt)}
                      </p>
                    </button>
                  ))
                )}
              </div>
            </div>
          ) : null}
        </div>

        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => {
              setMenuOpen((v) => !v);
              setNotifOpen(false);
            }}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-brand text-xs font-semibold text-white"
            aria-label="User menu"
          >
            {user ? initials(user.name) : "—"}
          </button>

          {menuOpen ? (
            <div className="absolute right-0 z-50 mt-2 w-52 rounded-xl border border-line bg-surface py-1.5 shadow-lg">
              <div className="border-b border-line px-3 py-2">
                <p className="truncate text-sm font-medium text-ink">
                  {user?.name}
                </p>
                <p className="truncate text-xs text-muted">{user?.email}</p>
              </div>
              <button
                type="button"
                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-muted hover:bg-canvas hover:text-ink"
                onClick={() => {
                  setMenuOpen(false);
                  router.push("/profile");
                }}
              >
                <UserRound className="h-4 w-4" />
                Profile
              </button>
              <button
                type="button"
                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-muted hover:bg-canvas hover:text-ink"
                onClick={() => void handleLogout()}
              >
                <LogOut className="h-4 w-4" />
                Logout
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
