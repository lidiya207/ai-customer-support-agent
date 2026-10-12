"use client";

import { useEffect, useState } from "react";
import {
  MessageSquare,
  CheckCircle2,
  AlertTriangle,
  Ticket,
} from "lucide-react";
import { ConversationTable } from "@/components/dashboard/conversation-table";
import { SimpleBarChart } from "@/components/dashboard/simple-bar-chart";
import { StatCard } from "@/components/ui/stat-card";
import {
  getAnalyticsOverview,
  listConversations,
} from "@/lib/api";
import { conversationActivity } from "@/lib/mock-data";
import type { Conversation, DashboardStats } from "@/lib/types";

const emptyStats: DashboardStats = {
  totalConversations: 0,
  totalConversationsChange: "No data yet",
  aiResolved: 0,
  resolutionRate: "0%",
  escalated: 0,
  escalationRate: "0%",
  openTickets: 0,
  highPriority: 0,
};

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>(emptyStats);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [overview, convs] = await Promise.all([
          getAnalyticsOverview(),
          listConversations(),
        ]);
        if (!cancelled) {
          setStats(overview);
          setConversations(convs);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load dashboard");
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
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          Dashboard
        </h1>
        <p className="mt-1 text-sm text-muted">
          Overview of AI customer support activity.
        </p>
        {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Total Conversations"
          value={stats.totalConversations.toLocaleString()}
          subtitle={stats.totalConversationsChange}
          icon={<MessageSquare className="h-4 w-4" />}
        />
        <StatCard
          title="AI Resolved"
          value={stats.aiResolved.toLocaleString()}
          subtitle={stats.resolutionRate}
          icon={<CheckCircle2 className="h-4 w-4" />}
        />
        <StatCard
          title="Escalated"
          value={stats.escalated.toLocaleString()}
          subtitle={stats.escalationRate}
          icon={<AlertTriangle className="h-4 w-4" />}
        />
        <StatCard
          title="Open Tickets"
          value={stats.openTickets}
          subtitle={`${stats.highPriority} high priority`}
          icon={<Ticket className="h-4 w-4" />}
        />
      </div>

      <div className="rounded-xl border border-line bg-surface p-5">
        <h2 className="font-display text-base font-semibold text-ink">
          Conversation Activity
        </h2>
        <p className="mt-1 text-sm text-muted">
          Sample weekly pattern (live daily metrics coming next)
        </p>
        <div className="mt-4">
          <SimpleBarChart data={conversationActivity} />
        </div>
      </div>

      <div>
        <h2 className="mb-3 font-display text-base font-semibold text-ink">
          Recent Conversations
        </h2>
        <ConversationTable
          conversations={conversations.slice(0, 4)}
          showTopic
        />
      </div>
    </div>
  );
}
