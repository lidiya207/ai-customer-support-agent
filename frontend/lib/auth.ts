/** Auth types and centralized JWT token storage (localStorage). */

export type UserRole = "customer" | "support_agent" | "admin";

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

const TOKEN_KEY = "ai_support_access_token";
const USER_KEY = "ai_support_user";

/**
 * Token storage is centralized here so it can be swapped later for HttpOnly cookies.
 *
 * Tradeoff of localStorage JWTs:
 * - Pros: simple cross-origin setup (Next :3000 ↔ FastAPI :8000) without Secure cookie constraints on localhost HTTP.
 * - Cons: accessible to JavaScript (XSS risk). Prefer HttpOnly Secure cookies in production when serving over HTTPS / same-site.
 */
export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function setAuthSession(token: string, user: AuthUser): void {
  window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuthSession(): void {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

export function getRedirectPathForRole(role: UserRole): string {
  if (role === "customer") return "/chat";
  return "/dashboard";
}
