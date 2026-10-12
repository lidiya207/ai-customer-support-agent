"use client";

import { useEffect, useMemo, useState } from "react";
import { X } from "lucide-react";
import { AgentRunTable } from "@/components/dashboard/agent-run-table";
import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/ui/stat-card";
import { listAgentRuns } from "@/lib/api";
import type { AgentRun } from "@/lib/types";

export default function AgentsPage() {
  const [selected, setSelected] = useState<AgentRun | null>(null);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await listAgentRuns();
        if (!cancelled) setRuns(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load runs");
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const stats = useMemo(() => {
    const toolCalls = runs.reduce(
      (sum, run) =>
        sum +
        (run.details.toolCalls === "none"
          ? 0
          : run.details.toolCalls.split(",").filter(Boolean).length),
      0
    );
    const success = runs.filter((r) => r.status === "success").length;
    const avg =
      runs.length === 0
        ? "0 ms"
        : `${Math.round(
            runs.reduce((sum, r) => sum + parseInt(r.latency, 10) || 0, 0) /
              runs.length
          )} ms`;
    return {
      agentRuns: runs.length,
      toolCalls,
      averageLatency: avg,
      successfulRuns: `${success}/${runs.length || 0}`,
    };
  }, [runs]);

  return (
    <div className="space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">
          Agent Activity
        </h1>
        <p className="mt-1 text-sm text-muted">
          Inspect how the AI agent reasons, selects tools, and responds.
        </p>
        {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard title="Agent Runs" value={stats.agentRuns.toLocaleString()} />
        <StatCard title="Tool Calls" value={stats.toolCalls.toLocaleString()} />
        <StatCard title="Average Latency" value={stats.averageLatency} />
        <StatCard title="Successful Runs" value={stats.successfulRuns} />
      </div>

      <div>
        <h2 className="mb-3 text-base font-semibold text-ink">Agent Runs</h2>
        <AgentRunTable
          runs={runs}
          selectedId={selected?.id}
          onSelect={setSelected}
        />
      </div>

      {selected ? (
        <div className="fixed inset-0 z-50 flex justify-end">
          <button
            type="button"
            className="absolute inset-0 bg-black/40"
            aria-label="Close panel"
            onClick={() => setSelected(null)}
          />
          <aside className="relative flex h-full w-full max-w-lg flex-col border-l border-line bg-surface shadow-xl">
            <div className="flex items-center justify-between border-b border-line px-5 py-4">
              <div>
                <h2 className="text-base font-semibold text-ink">
                  Agent Run Detail
                </h2>
                <p className="text-xs text-muted">{selected.id}</p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setSelected(null)}>
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="flex-1 space-y-5 overflow-y-auto p-5 text-sm">
              {(
                [
                  ["User Input", selected.details.userInput],
                  ["Detected Intent", selected.details.detectedIntent],
                  ["Agent Decision", selected.details.agentDecision],
                  ["Knowledge Retrieved", selected.details.knowledgeRetrieved],
                  ["Tool Calls", selected.details.toolCalls],
                  ["Tool Input", selected.details.toolInput],
                  ["Tool Output", selected.details.toolOutput],
                  ["Final Response", selected.details.finalResponse],
                  ["Execution Time", selected.details.executionTime],
                ] as const
              ).map(([label, value]) => (
                <div key={label}>
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted/70">
                    {label}
                  </p>
                  {label === "Tool Input" || label === "Tool Output" ? (
                    <pre className="overflow-x-auto rounded-lg bg-canvas p-3 font-mono text-xs text-ink">
                      {value}
                    </pre>
                  ) : label === "Detected Intent" || label === "Tool Calls" ? (
                    <code className="rounded bg-canvas px-2 py-1 text-xs text-ink">
                      {value}
                    </code>
                  ) : (
                    <p className="leading-relaxed text-ink">{value}</p>
                  )}
                </div>
              ))}
            </div>
          </aside>
        </div>
      ) : null}
    </div>
  );
}
