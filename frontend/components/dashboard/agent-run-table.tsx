"use client";

import { StatusBadge } from "@/components/ui/status-badge";
import type { AgentRun } from "@/lib/types";

interface AgentRunTableProps {
  runs: AgentRun[];
  selectedId?: string | null;
  onSelect?: (run: AgentRun) => void;
}

export function AgentRunTable({
  runs,
  selectedId,
  onSelect,
}: AgentRunTableProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-line bg-surface">
      <table className="w-full min-w-[900px] text-left text-sm">
        <thead>
          <tr className="border-b border-line bg-canvas">
            <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">
              Input
            </th>
            <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">
              Intent
            </th>
            <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">
              Action
            </th>
            <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">
              Tool
            </th>
            <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">
              Confidence
            </th>
            <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">
              Latency
            </th>
            <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">
              Status
            </th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr
              key={run.id}
              onClick={() => onSelect?.(run)}
              className={`border-b border-line/70 last:border-0 hover:bg-canvas ${
                onSelect ? "cursor-pointer" : ""
              } ${selectedId === run.id ? "bg-accent-soft" : ""}`}
            >
              <td className="max-w-[220px] truncate px-4 py-2.5 font-medium text-ink">
                &ldquo;{run.input}&rdquo;
              </td>
              <td className="px-4 py-2.5">
                <code className="rounded bg-canvas px-1.5 py-0.5 text-xs text-ink/80">
                  {run.intent}
                </code>
              </td>
              <td className="px-4 py-2.5 text-muted">{run.action}</td>
              <td className="px-4 py-2.5">
                <code className="rounded bg-canvas px-1.5 py-0.5 text-xs text-ink/80">
                  {run.tool}
                </code>
              </td>
              <td className="px-4 py-2.5 text-ink/80">{run.confidence}%</td>
              <td className="px-4 py-2.5 text-muted">{run.latency}</td>
              <td className="px-4 py-2.5">
                <StatusBadge status={run.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
