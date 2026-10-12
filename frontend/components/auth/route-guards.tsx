"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import type { UserRole } from "@/lib/auth";

function LoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-atmosphere">
      <p className="text-sm text-muted">Loading…</p>
    </div>
  );
}

/** Require any authenticated user. Redirects to /login when unauthenticated. */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, isLoading, isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading || !user) {
    return <LoadingScreen />;
  }

  return <>{children}</>;
}

/** Require support_agent or admin. Customers are redirected to /chat. */
export function RequireStaff({ children }: { children: React.ReactNode }) {
  const { user, isLoading, isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }
    if (user && user.role === "customer") {
      router.replace("/chat");
    }
  }, [isLoading, isAuthenticated, user, router]);

  const allowed: UserRole[] = ["support_agent", "admin"];
  if (isLoading || !user || !allowed.includes(user.role)) {
    return <LoadingScreen />;
  }

  return <>{children}</>;
}
