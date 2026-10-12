"use client";

import { FormEvent, use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2 } from "lucide-react";
import { ChatMessage } from "@/components/chat/chat-message";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  claimConversation,
  getConversation,
  replyToConversation,
  updateConversation,
} from "@/lib/api";
import type { ConversationDetail } from "@/lib/types";

export default function ConversationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [conversation, setConversation] = useState<ConversationDetail | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function initial() {
      try {
        const data = await getConversation(id);
        if (!cancelled) setConversation(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load");
        }
      }
    }
    void initial();
    return () => {
      cancelled = true;
    };
  }, [id]);

  // Live updates so the agent sees new customer messages while replying.
  useEffect(() => {
    if (!id) return;
    const timer = window.setInterval(() => {
      void (async () => {
        try {
          const data = await getConversation(id);
          setConversation(data);
        } catch {
          // Ignore transient poll errors.
        }
      })();
    }, 3000);
    return () => window.clearInterval(timer);
  }, [id]);

  async function handleClaim() {
    setBusy(true);
    setActionError(null);
    try {
      const data = await claimConversation(id);
      setConversation(data);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Claim failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleReply(e: FormEvent) {
    e.preventDefault();
    const content = reply.trim();
    if (!content || busy) return;
    setBusy(true);
    setActionError(null);
    try {
      const data = await replyToConversation(id, content);
      setConversation(data);
      setReply("");
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Reply failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleReenableAi() {
    setBusy(true);
    setActionError(null);
    try {
      const data = await updateConversation(id, { ai_enabled: true });
      setConversation(data);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleResolve() {
    setBusy(true);
    setActionError(null);
    try {
      const data = await updateConversation(id, { status: "resolved" });
      setConversation(data);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Resolve failed");
    } finally {
      setBusy(false);
    }
  }

  if (error) {
    return (
      <div className="p-6">
        <Link
          href="/dashboard/conversations"
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back
        </Link>
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  if (!conversation) {
    return <div className="p-6 text-sm text-muted">Loading conversation...</div>;
  }

  const aiPaused = conversation.aiEnabled === false;

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      <div className="border-b border-line bg-surface px-4 py-3 md:px-6">
        <Link
          href="/dashboard/conversations"
          className="mb-2 inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to conversations
        </Link>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-lg font-semibold text-ink">
            {conversation.customer}
          </h1>
          <StatusBadge status={conversation.status} />
          <span className="text-sm text-muted">{conversation.topic}</span>
          {aiPaused ? (
            <span className="rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800">
              AI paused · human handoff
            </span>
          ) : (
            <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-800">
              AI active
            </span>
          )}
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => void handleClaim()}
          >
            Take ownership
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={busy || !aiPaused}
            onClick={() => void handleReenableAi()}
          >
            Re-enable AI
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => void handleResolve()}
          >
            Mark resolved
          </Button>
        </div>
        {actionError ? (
          <p className="mt-2 text-sm text-red-600">{actionError}</p>
        ) : null}
      </div>

      <div className="grid min-h-0 flex-1 lg:grid-cols-[240px_1fr_300px]">
        <aside className="overflow-y-auto border-b border-line bg-surface p-4 lg:border-b-0 lg:border-r">
          <h2 className="mb-4 text-xs font-semibold uppercase tracking-wider text-muted/70">
            Conversation Info
          </h2>
          <dl className="space-y-4 text-sm">
            <div>
              <dt className="text-muted">Customer</dt>
              <dd className="mt-0.5 font-medium text-ink">
                {conversation.customer}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Email</dt>
              <dd className="mt-0.5 text-ink">{conversation.email}</dd>
            </div>
            <div>
              <dt className="text-muted">Assigned agent</dt>
              <dd className="mt-0.5 text-ink">
                {conversation.assignedAgent || "Unassigned"}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Conversation ID</dt>
              <dd className="mt-0.5 font-mono text-xs text-ink">
                {conversation.id}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Created Date</dt>
              <dd className="mt-0.5 text-ink">{conversation.createdAt}</dd>
            </div>
            <div>
              <dt className="text-muted">Status</dt>
              <dd className="mt-1">
                <StatusBadge status={conversation.status} />
              </dd>
            </div>
          </dl>
        </aside>

        <section className="flex min-h-0 flex-col bg-canvas">
          <div className="flex-1 overflow-y-auto p-4 md:p-6">
            <div className="mx-auto flex max-w-2xl flex-col gap-4">
              {conversation.messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
            </div>
          </div>
          <form
            onSubmit={(e) => void handleReply(e)}
            className="border-t border-line bg-surface p-4"
          >
            <p className="mb-2 text-xs text-muted">
              Reply as a human agent. Sending a reply pauses AI auto-replies.
            </p>
            <div className="mx-auto flex max-w-2xl gap-2">
              <textarea
                value={reply}
                onChange={(e) => setReply(e.target.value)}
                rows={2}
                disabled={busy}
                placeholder="Write a reply to the customer..."
                className="min-h-11 flex-1 resize-none rounded-xl border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/15 disabled:opacity-60"
              />
              <Button type="submit" disabled={busy || !reply.trim()}>
                Send reply
              </Button>
            </div>
          </form>
        </section>

        <aside className="overflow-y-auto border-t border-line bg-surface p-4 lg:border-l lg:border-t-0">
          <h2 className="mb-4 text-xs font-semibold uppercase tracking-wider text-muted/70">
            AI Agent Details
          </h2>

          <div className="space-y-4 text-sm">
            <div>
              <p className="text-muted">Detected Intent</p>
              <code className="mt-1 inline-block rounded bg-canvas px-2 py-1 text-xs text-ink">
                {conversation.agentDetails.detectedIntent}
              </code>
            </div>
            <div>
              <p className="text-muted">Confidence</p>
              <p className="mt-0.5 font-semibold text-ink">
                {conversation.agentDetails.confidence}%
              </p>
            </div>
            <div>
              <p className="text-muted">Agent Status</p>
              <p className="mt-0.5 font-medium text-ink">
                {conversation.agentDetails.agentStatus}
              </p>
            </div>
            <div>
              <p className="text-muted">Tools Used</p>
              <div className="mt-1 flex flex-wrap gap-1">
                {conversation.agentDetails.toolsUsed.length ? (
                  conversation.agentDetails.toolsUsed.map((tool) => (
                    <code
                      key={tool}
                      className="rounded bg-canvas px-2 py-0.5 text-xs text-ink"
                    >
                      {tool}
                    </code>
                  ))
                ) : (
                  <span className="text-ink">None</span>
                )}
              </div>
            </div>
          </div>

          <div className="mt-8">
            <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-muted/70">
              Agent Execution
            </h3>
            <ol className="space-y-0">
              {conversation.agentDetails.timeline.map((step, index) => (
                <li key={step.id} className="relative flex gap-3 pb-5 last:pb-0">
                  {index < conversation.agentDetails.timeline.length - 1 ? (
                    <span className="absolute left-[11px] top-6 h-[calc(100%-16px)] w-px bg-line" />
                  ) : null}
                  <span className="relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent text-white">
                    {index === conversation.agentDetails.timeline.length - 1 ? (
                      <CheckCircle2 className="h-3.5 w-3.5" />
                    ) : (
                      <span className="text-[10px] font-semibold">{index + 1}</span>
                    )}
                  </span>
                  <div className="min-w-0 pt-0.5">
                    <p className="text-sm font-medium text-ink">{step.label}</p>
                    {step.description ? (
                      <p className="mt-0.5 text-xs text-muted">
                        {step.description}
                      </p>
                    ) : null}
                    <p className="mt-0.5 text-[11px] text-muted/70">
                      {step.timestamp}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </aside>
      </div>
    </div>
  );
}
