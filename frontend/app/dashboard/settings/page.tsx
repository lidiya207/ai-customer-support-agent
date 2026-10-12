"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getSettings, saveSettings } from "@/lib/api";
import type { AppSettings } from "@/lib/types";

const sections = [
  "General",
  "AI Model",
  "Escalation Rules",
  "Integrations",
] as const;

export default function SettingsPage() {
  const [active, setActive] = useState<(typeof sections)[number]>("AI Model");
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await getSettings();
        if (!cancelled) setSettings(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load settings");
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSave(partial: Partial<AppSettings>) {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const next = await saveSettings(partial);
      setSettings(next);
      setSuccess("Settings saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  if (!settings) {
    return (
      <div className="p-6 text-sm text-muted">
        {error || "Loading settings…"}
      </div>
    );
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">
          Settings
        </h1>
        <p className="mt-1 text-sm text-muted">
          Configure AI prompts and escalation rules. Changes are saved to the
          backend (admin can update; support can view).
        </p>
        {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
        {success ? <p className="mt-2 text-sm text-emerald-600">{success}</p> : null}
      </div>

      <div className="grid gap-6 lg:grid-cols-[200px_1fr]">
        <nav className="space-y-1">
          {sections.map((section) => (
            <button
              key={section}
              type="button"
              onClick={() => setActive(section)}
              className={`block w-full rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors ${
                active === section
                  ? "bg-canvas text-ink"
                  : "text-muted hover:bg-canvas hover:text-ink"
              }`}
            >
              {section}
            </button>
          ))}
        </nav>

        <div className="rounded-2xl border border-line/80 bg-surface/90 p-5 shadow-sm md:p-6">
          {active === "General" ? (
            <div className="space-y-4">
              <h2 className="text-base font-semibold text-ink">General</h2>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-ink/80">
                  Workspace Name
                </label>
                <Input
                  value={settings.workspace_name}
                  onChange={(e) =>
                    setSettings({ ...settings, workspace_name: e.target.value })
                  }
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-ink/80">
                  Support Email
                </label>
                <Input
                  value={settings.support_email}
                  onChange={(e) =>
                    setSettings({ ...settings, support_email: e.target.value })
                  }
                />
              </div>
              <Button
                disabled={saving}
                onClick={() =>
                  void handleSave({
                    workspace_name: settings.workspace_name,
                    support_email: settings.support_email,
                  })
                }
              >
                Save changes
              </Button>
            </div>
          ) : null}

          {active === "AI Model" ? (
            <div className="space-y-4">
              <h2 className="text-base font-semibold text-ink">AI Model</h2>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-ink/80">
                  Model override (optional)
                </label>
                <Input
                  value={settings.model_override}
                  onChange={(e) =>
                    setSettings({ ...settings, model_override: e.target.value })
                  }
                  placeholder="Leave blank to use .env model"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-ink/80">
                  Temperature
                </label>
                <Input
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  value={String(settings.temperature)}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      temperature: Number(e.target.value),
                    })
                  }
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-ink/80">
                  System Prompt
                </label>
                <textarea
                  value={settings.system_prompt}
                  onChange={(e) =>
                    setSettings({ ...settings, system_prompt: e.target.value })
                  }
                  rows={8}
                  className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15"
                />
              </div>
              <Button
                disabled={saving}
                onClick={() =>
                  void handleSave({
                    system_prompt: settings.system_prompt,
                    model_override: settings.model_override,
                    temperature: settings.temperature,
                  })
                }
              >
                Save model settings
              </Button>
            </div>
          ) : null}

          {active === "Escalation Rules" ? (
            <div className="space-y-4">
              <h2 className="text-base font-semibold text-ink">
                Escalation Rules
              </h2>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-ink/80">
                  Confidence threshold (escalate below)
                </label>
                <Input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={String(settings.confidence_threshold)}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      confidence_threshold: Number(e.target.value),
                    })
                  }
                />
                <p className="mt-1 text-xs text-muted">
                  Example: 0.6 means escalate when confidence is under 60%.
                </p>
              </div>
              <label className="flex items-center gap-2 text-sm text-ink/80">
                <input
                  type="checkbox"
                  checked={settings.escalate_refunds}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      escalate_refunds: e.target.checked,
                    })
                  }
                />
                Auto-escalate refund requests
              </label>
              <label className="flex items-center gap-2 text-sm text-ink/80">
                <input
                  type="checkbox"
                  checked={settings.escalate_complaints}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      escalate_complaints: e.target.checked,
                    })
                  }
                />
                Auto-escalate complaints
              </label>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-ink/80">
                  Max failed tool calls before escalate
                </label>
                <Input
                  type="number"
                  min="1"
                  max="10"
                  value={String(settings.max_failed_tools)}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      max_failed_tools: Number(e.target.value),
                    })
                  }
                />
              </div>
              <Button
                disabled={saving}
                onClick={() =>
                  void handleSave({
                    confidence_threshold: settings.confidence_threshold,
                    escalate_refunds: settings.escalate_refunds,
                    escalate_complaints: settings.escalate_complaints,
                    max_failed_tools: settings.max_failed_tools,
                  })
                }
              >
                Save rules
              </Button>
            </div>
          ) : null}

          {active === "Integrations" ? (
            <div className="space-y-4">
              <h2 className="text-base font-semibold text-ink">
                Integrations
              </h2>
              <div className="space-y-3">
                {[
                  { name: "Ollama / OpenAI", status: "Configured via .env" },
                  { name: "MySQL", status: "Connected" },
                  { name: "Vector RAG (local embeddings)", status: "Enabled" },
                  { name: "Email / Slack", status: "Coming soon" },
                ].map((item) => (
                  <div
                    key={item.name}
                    className="flex items-center justify-between rounded-lg border border-line px-4 py-3"
                  >
                    <span className="text-sm font-medium text-ink">
                      {item.name}
                    </span>
                    <span className="text-xs text-muted">{item.status}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
