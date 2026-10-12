"use client";

import { FormEvent, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Eye, EyeOff } from "lucide-react";
import { RequireAuth } from "@/components/auth/route-guards";
import { useAuth } from "@/components/auth/auth-provider";
import { BrandMark } from "@/components/ui/brand-mark";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, changePassword, updateProfile } from "@/lib/api";
import type { UserRole } from "@/lib/auth";

function roleLabel(role: UserRole) {
  if (role === "admin") return "Admin";
  if (role === "support_agent") return "Support Agent";
  return "Customer";
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

function ProfilePageContent() {
  const { user, setUser, redirectPathForRole } = useAuth();

  const [name, setName] = useState(user?.name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileSuccess, setProfileSuccess] = useState<string | null>(null);
  const [savingProfile, setSavingProfile] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);
  const [savingPassword, setSavingPassword] = useState(false);

  const backHref = useMemo(
    () => (user ? redirectPathForRole(user.role) : "/"),
    [user, redirectPathForRole]
  );

  async function handleProfileSubmit(event: FormEvent) {
    event.preventDefault();
    setProfileError(null);
    setProfileSuccess(null);
    setSavingProfile(true);

    try {
      const updated = await updateProfile({
        name: name.trim(),
        email: email.trim(),
      });
      setUser(updated);
      setName(updated.name);
      setEmail(updated.email);
      setProfileSuccess("Profile updated successfully.");
    } catch (err) {
      if (err instanceof ApiError) {
        setProfileError(err.detail);
      } else {
        setProfileError("Unable to update profile. Please try again.");
      }
    } finally {
      setSavingProfile(false);
    }
  }

  async function handlePasswordSubmit(event: FormEvent) {
    event.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(null);

    if (newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("New password and confirmation do not match.");
      return;
    }

    setSavingPassword(true);
    try {
      const result = await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPasswordSuccess(result.detail);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      if (err instanceof ApiError) {
        setPasswordError(err.detail);
      } else {
        setPasswordError("Unable to change password. Please try again.");
      }
    } finally {
      setSavingPassword(false);
    }
  }

  if (!user) return null;

  return (
    <div className="min-h-screen bg-canvas">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4">
          <Link href="/">
            <BrandMark />
          </Link>
          <Link
            href={backHref}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-muted hover:text-ink"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl space-y-6 px-4 py-8">
        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-brand text-lg font-semibold text-white">
            {initials(user.name)}
          </div>
          <div>
            <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
              Profile
            </h1>
            <p className="mt-1 text-sm text-muted">
              Manage your account details and password.
            </p>
          </div>
        </div>

        <section className="rounded-2xl border border-line/80 bg-surface/90 p-5 shadow-sm md:p-6">
          <div className="mb-5 flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-ink">
              Account details
            </h2>
            <span className="rounded-md bg-canvas px-2.5 py-1 text-xs font-medium text-muted">
              {roleLabel(user.role)}
            </span>
          </div>

          <form onSubmit={handleProfileSubmit} className="space-y-4">
            {profileError ? (
              <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {profileError}
              </div>
            ) : null}
            {profileSuccess ? (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                {profileSuccess}
              </div>
            ) : null}

            <div className="space-y-1.5">
              <label htmlFor="name" className="text-sm font-medium text-ink/80">
                Full name
              </label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                disabled={savingProfile}
                autoComplete="name"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="email" className="text-sm font-medium text-ink/80">
                Email
              </label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={savingProfile}
                autoComplete="email"
              />
            </div>

            <Button type="submit" disabled={savingProfile}>
              {savingProfile ? "Saving…" : "Save changes"}
            </Button>
          </form>
        </section>

        <section className="rounded-2xl border border-line/80 bg-surface/90 p-5 shadow-sm md:p-6">
          <h2 className="mb-5 text-base font-semibold text-ink">
            Change password
          </h2>

          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            {passwordError ? (
              <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {passwordError}
              </div>
            ) : null}
            {passwordSuccess ? (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                {passwordSuccess}
              </div>
            ) : null}

            <div className="space-y-1.5">
              <label
                htmlFor="current-password"
                className="text-sm font-medium text-ink/80"
              >
                Current password
              </label>
              <div className="relative">
                <Input
                  id="current-password"
                  type={showCurrent ? "text" : "password"}
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  required
                  disabled={savingPassword}
                  autoComplete="current-password"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowCurrent((v) => !v)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-muted/70 hover:text-ink/80"
                  aria-label={showCurrent ? "Hide password" : "Show password"}
                >
                  {showCurrent ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="new-password"
                className="text-sm font-medium text-ink/80"
              >
                New password
              </label>
              <div className="relative">
                <Input
                  id="new-password"
                  type={showNew ? "text" : "password"}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                  disabled={savingPassword}
                  autoComplete="new-password"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowNew((v) => !v)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-muted/70 hover:text-ink/80"
                  aria-label={showNew ? "Hide password" : "Show password"}
                >
                  {showNew ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="confirm-password"
                className="text-sm font-medium text-ink/80"
              >
                Confirm new password
              </label>
              <Input
                id="confirm-password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={8}
                disabled={savingPassword}
                autoComplete="new-password"
              />
            </div>

            <Button type="submit" disabled={savingPassword}>
              {savingPassword ? "Updating…" : "Update password"}
            </Button>
          </form>
        </section>
      </main>
    </div>
  );
}

export default function ProfilePage() {
  return (
    <RequireAuth>
      <ProfilePageContent />
    </RequireAuth>
  );
}
