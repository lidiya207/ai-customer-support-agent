"use client";

import { useRouter } from "next/navigation";
import { StatusBadge } from "@/components/ui/status-badge";
import type { Conversation } from "@/lib/types";

interface ConversationTableProps {
  conversations: Conversation[];
  showTopic?: boolean;
  showLastMessage?: boolean;
  showIntent?: boolean;
  linkable?: boolean;
}

export function ConversationTable({
  conversations,
  showTopic = true,
  showLastMessage = false,
  showIntent = false,
  linkable = true,
}: ConversationTableProps) {
  const router = useRouter();

  return (
    <div className="overflow-x-auto rounded-xl border border-line bg-surface">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead>
          <tr className="border-b border-line bg-canvas">
            <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">
              Customer
            </th>
            {showTopic ? (
              <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">
                Topic
              </th>
            ) : null}
            {showLastMessage ? (
              <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">
                Last Message
              </th>
            ) : null}
            {showIntent ? (
              <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">
                Intent
              </th>
            ) : null}
            <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">
              {showTopic && !showLastMessage ? "AI Confidence" : "Confidence"}
            </th>
            <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">
              Status
            </th>
            <th className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted">
              {showLastMessage ? "Updated" : "Time"}
            </th>
          </tr>
        </thead>
        <tbody>
          {conversations.map((conversation) => (
            <tr
              key={conversation.id}
              onClick={() => {
                if (linkable) {
                  router.push(`/dashboard/conversations/${conversation.id}`);
                }
              }}
              className={`border-b border-line/70 last:border-0 hover:bg-canvas ${
                linkable ? "cursor-pointer" : ""
              }`}
            >
              <td className="px-4 py-2.5 font-medium text-ink">
                {conversation.customer}
              </td>
              {showTopic ? (
                <td className="px-4 py-2.5 text-muted">{conversation.topic}</td>
              ) : null}
              {showLastMessage ? (
                <td className="max-w-[240px] truncate px-4 py-2.5 text-muted">
                  &ldquo;{conversation.lastMessage}&rdquo;
                </td>
              ) : null}
              {showIntent ? (
                <td className="px-4 py-2.5">
                  <code className="rounded bg-canvas px-1.5 py-0.5 text-xs text-ink/80">
                    {conversation.intent}
                  </code>
                </td>
              ) : null}
              <td className="px-4 py-2.5 text-ink/80">
                {conversation.confidence}%
              </td>
              <td className="px-4 py-2.5">
                <StatusBadge status={conversation.status} />
              </td>
              <td className="px-4 py-2.5 text-muted">
                {conversation.updatedAt}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
