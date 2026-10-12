"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { StatusBadge } from "@/components/ui/status-badge";
import { StatCard } from "@/components/ui/stat-card";
import { useAuth } from "@/components/auth/auth-provider";
import { listTickets, updateTicket } from "@/lib/api";
import type { Ticket, TicketStatus } from "@/lib/types";

const STATUS_OPTIONS: TicketStatus[] = [
  "open",
  "in_progress",
  "waiting",
  "resolved",
];

export default function TicketsPage() {
  const { user } = useAuth();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);

  async function load() {
    const data = await listTickets();
    setTickets(data);
  }

  useEffect(() => {
    let cancelled = false;
    async function initial() {
      try {
        const data = await listTickets();
        if (!cancelled) setTickets(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load tickets");
        }
      }
    }
    void initial();
    return () => {
      cancelled = true;
    };
  }, []);

  const stats = useMemo(
    () => ({
      open: tickets.filter((t) => t.status === "open").length,
      inProgress: tickets.filter((t) => t.status === "in_progress").length,
      waiting: tickets.filter((t) => t.status === "waiting").length,
      resolved: tickets.filter((t) => t.status === "resolved").length,
    }),
    [tickets]
  );

  async function handleStatusChange(ticketId: string, status: string) {
    setSavingId(ticketId);
    setError(null);
    try {
      await updateTicket(ticketId, { status });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update status");
    } finally {
      setSavingId(null);
    }
  }

  async function handleAssignMe(ticketId: string) {
    if (!user?.name) return;
    setSavingId(ticketId);
    setError(null);
    try {
      await updateTicket(ticketId, {
        assigned_agent: user.name,
        status: "in_progress",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to assign ticket");
    } finally {
      setSavingId(null);
    }
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">
          Support Tickets
        </h1>
        <p className="mt-1 text-sm text-muted">
          Track, assign, and update escalated customer issues.
        </p>
        {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard title="Open" value={stats.open} />
        <StatCard title="In Progress" value={stats.inProgress} />
        <StatCard title="Waiting" value={stats.waiting} />
        <StatCard title="Resolved" value={stats.resolved} />
      </div>

      <div className="overflow-x-auto rounded-2xl border border-line/80 bg-surface/90">
        <table className="w-full min-w-[960px] text-left text-sm">
          <thead>
            <tr className="border-b border-line bg-canvas/80">
              <th className="px-4 py-3 font-medium text-muted">Ticket</th>
              <th className="px-4 py-3 font-medium text-muted">Customer</th>
              <th className="px-4 py-3 font-medium text-muted">Category</th>
              <th className="px-4 py-3 font-medium text-muted">Priority</th>
              <th className="px-4 py-3 font-medium text-muted">Assigned To</th>
              <th className="px-4 py-3 font-medium text-muted">Status</th>
              <th className="px-4 py-3 font-medium text-muted">Created</th>
              <th className="px-4 py-3 font-medium text-muted">Actions</th>
            </tr>
          </thead>
          <tbody>
            {tickets.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-muted">
                  No tickets yet. Escalate a chat to create one.
                </td>
              </tr>
            ) : (
              tickets.map((ticket) => (
                <tr
                  key={ticket.id}
                  className="border-b border-line/60 last:border-0 hover:bg-canvas/80"
                >
                  <td className="px-4 py-3 font-mono text-xs font-medium text-ink">
                    {ticket.id}
                  </td>
                  <td className="px-4 py-3 font-medium text-ink">
                    {ticket.customer}
                  </td>
                  <td className="px-4 py-3 text-muted">{ticket.category}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={ticket.priority} />
                  </td>
                  <td className="px-4 py-3 text-muted">{ticket.assignedTo}</td>
                  <td className="px-4 py-3">
                    <select
                      value={ticket.status}
                      disabled={savingId === ticket.id}
                      onChange={(e) =>
                        void handleStatusChange(ticket.id, e.target.value)
                      }
                      className="rounded-md border border-line bg-surface px-2 py-1 text-xs text-ink outline-none focus:border-accent"
                    >
                      {STATUS_OPTIONS.map((status) => (
                        <option key={status} value={status}>
                          {status.replace(/_/g, " ")}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-3 text-muted">{ticket.createdAt}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        disabled={savingId === ticket.id}
                        onClick={() => void handleAssignMe(ticket.id)}
                        className="rounded-md border border-line px-2 py-1 text-xs font-medium text-ink/80 hover:bg-canvas disabled:opacity-50"
                      >
                        Assign me
                      </button>
                      {ticket.conversationId ? (
                        <Link
                          href={`/dashboard/conversations/${ticket.conversationId}`}
                          className="rounded-md border border-line px-2 py-1 text-xs font-medium text-ink/80 hover:bg-canvas"
                        >
                          Open chat
                        </Link>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
