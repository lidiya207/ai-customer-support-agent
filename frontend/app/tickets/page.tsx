"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Ticket } from "lucide-react";
import { RequireAuth } from "@/components/auth/route-guards";
import { StatusBadge } from "@/components/ui/status-badge";
import { listMyTickets } from "@/lib/api";
import type { Ticket as TicketType } from "@/lib/types";

function MyTicketsContent() {
  const [tickets, setTickets] = useState<TicketType[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await listMyTickets();
        if (!cancelled) setTickets(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load tickets");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="min-h-screen bg-canvas">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-4">
          <Link
            href="/chat"
            className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to chat
          </Link>
          <p className="font-display text-sm font-semibold text-ink">My Tickets</p>
          <span className="w-20" />
        </div>
      </header>

      <main className="mx-auto max-w-3xl space-y-4 px-4 py-6">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Support tickets</h1>
          <p className="mt-1 text-sm text-muted">
            Track status for issues escalated to a human agent.
          </p>
        </div>

        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        {loading ? (
          <p className="text-sm text-muted">Loading tickets…</p>
        ) : tickets.length === 0 ? (
          <div className="rounded-xl border border-dashed border-line bg-surface px-6 py-12 text-center">
            <Ticket className="mx-auto mb-3 h-8 w-8 text-muted/40" />
            <p className="text-sm font-medium text-ink">No tickets yet</p>
            <p className="mt-1 text-sm text-muted">
              Ask for a human in chat, or report a refund/complaint to create one.
            </p>
            <Link
              href="/chat"
              className="mt-4 inline-block text-sm font-medium text-ink underline"
            >
              Open chat
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {tickets.map((ticket) => (
              <article
                key={ticket.id}
                className="rounded-2xl border border-line/80 bg-surface/90 p-4 shadow-sm"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="font-mono text-xs font-medium text-muted">
                      {ticket.id}
                    </p>
                    <h2 className="mt-1 text-sm font-semibold text-ink">
                      {ticket.title || ticket.category}
                    </h2>
                  </div>
                  <StatusBadge status={ticket.status} />
                </div>
                <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
                  <div>
                    <dt className="text-xs text-muted/70">Priority</dt>
                    <dd className="mt-0.5">
                      <StatusBadge status={ticket.priority} />
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted/70">Assigned to</dt>
                    <dd className="mt-0.5 text-ink">{ticket.assignedTo}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted/70">Created</dt>
                    <dd className="mt-0.5 text-ink">{ticket.createdAt}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

export default function MyTicketsPage() {
  return (
    <RequireAuth>
      <MyTicketsContent />
    </RequireAuth>
  );
}
