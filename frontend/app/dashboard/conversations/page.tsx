"use client";

import { useEffect, useMemo, useState } from "react";
import { ConversationTable } from "@/components/dashboard/conversation-table";
import { Input } from "@/components/ui/input";
import { listConversations } from "@/lib/api";
import type { Conversation, ConversationStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const filters: { label: string; value: "all" | ConversationStatus }[] = [
  { label: "All", value: "all" },
  { label: "Active", value: "active" },
  { label: "AI Resolved", value: "resolved" },
  { label: "Escalated", value: "escalated" },
  { label: "Closed", value: "closed" },
];

export default function ConversationsPage() {
  const [filter, setFilter] = useState<"all" | ConversationStatus>("all");
  const [search, setSearch] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await listConversations();
        if (!cancelled) setConversations(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load");
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    return conversations.filter((conversation) => {
      const matchesFilter = filter === "all" || conversation.status === filter;
      const query = search.toLowerCase();
      const matchesSearch =
        !query ||
        conversation.customer.toLowerCase().includes(query) ||
        conversation.lastMessage.toLowerCase().includes(query) ||
        conversation.intent.toLowerCase().includes(query);
      return matchesFilter && matchesSearch;
    });
  }, [conversations, filter, search]);

  return (
    <div className="space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">
          Conversations
        </h1>
        <p className="mt-1 text-sm text-muted">
          Monitor AI and customer support conversations.
        </p>
        {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2">
          {filters.map((item) => (
            <button
              key={item.value}
              type="button"
              onClick={() => setFilter(item.value)}
              className={cn(
                "rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors",
                filter === item.value
                  ? "border-brand bg-brand text-white"
                  : "border-line bg-surface text-muted hover:bg-canvas"
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search conversations..."
          className="sm:max-w-xs"
        />
      </div>

      <ConversationTable conversations={filtered} showTopic />
    </div>
  );
}
