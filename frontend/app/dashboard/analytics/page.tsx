"use client";

import { useEffect, useState } from "react";
import { SimpleBarChart } from "@/components/dashboard/simple-bar-chart";
import { StatCard } from "@/components/ui/stat-card";
import { getAnalyticsOverview } from "@/lib/api";
import { analyticsData, conversationActivity } from "@/lib/mock-data";
import type { DashboardStats } from "@/lib/types";

export default function AnalyticsPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await getAnalyticsOverview();
        if (!cancelled) setStats(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load analytics");
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">
          Analytics
        </h1>
        <p className="mt-1 text-sm text-muted">
          Measure AI support performance and escalation trends.
        </p>
        {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="AI Resolution Rate"
          value={stats?.resolutionRate ?? analyticsData.aiResolutionRate}
        />
        <StatCard
          title="Escalation Rate"
          value={stats?.escalationRate ?? analyticsData.escalationRate}
        />
        <StatCard
          title="Total Conversations"
          value={String(stats?.totalConversations ?? 0)}
        />
        <StatCard
          title="Open Tickets"
          value={String(stats?.openTickets ?? 0)}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-line/80 bg-surface/90 p-5 shadow-sm">
          <h2 className="text-base font-semibold text-ink">
            Conversation Volume
          </h2>
          <p className="mt-1 text-sm text-muted">Weekly pattern</p>
          <div className="mt-4">
            <SimpleBarChart data={conversationActivity} />
          </div>
        </div>
        <div className="rounded-2xl border border-line/80 bg-surface/90 p-5 shadow-sm">
          <h2 className="text-base font-semibold text-ink">Live Snapshot</h2>
          <ul className="mt-4 space-y-3 text-sm text-ink/80">
            <li>AI resolved: {stats?.aiResolved ?? 0}</li>
            <li>Escalated: {stats?.escalated ?? 0}</li>
            <li>High priority tickets: {stats?.highPriority ?? 0}</li>
            <li>{stats?.totalConversationsChange ?? "No conversations yet"}</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
