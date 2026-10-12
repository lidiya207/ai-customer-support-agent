"use client";

import { Bot, Headset, User, Wrench } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatMessage as ChatMessageType } from "@/lib/types";

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isCustomer = message.role === "customer";
  const isSystem = message.role === "system";
  const isAgent = message.role === "support_agent";

  if (isSystem) {
    return (
      <div className="mx-auto max-w-md rounded-xl border border-dashed border-line bg-canvas px-4 py-3 text-center">
        <div className="mb-1 flex items-center justify-center gap-1.5 text-xs font-medium text-muted">
          <Wrench className="h-3.5 w-3.5" />
          System
        </div>
        <p className="text-sm font-medium text-ink">{message.content}</p>
        {message.meta?.toolResult ? (
          <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-surface px-3 py-2 text-left text-xs text-muted">
            {message.meta.toolResult}
          </pre>
        ) : null}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex gap-2.5",
        isCustomer ? "flex-row-reverse" : "flex-row"
      )}
    >
      <div
        className={cn(
          "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isCustomer
            ? "bg-brand text-white"
            : isAgent
              ? "bg-emerald-600 text-white"
              : "bg-accent-soft text-accent"
        )}
      >
        {isCustomer ? (
          <User className="h-4 w-4" />
        ) : isAgent ? (
          <Headset className="h-4 w-4" />
        ) : (
          <Bot className="h-4 w-4" />
        )}
      </div>
      <div
        className={cn(
          "max-w-[78%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
          isCustomer
            ? "rounded-br-md bg-accent text-white"
            : isAgent
              ? "rounded-bl-md border border-emerald-200 bg-emerald-50 text-ink"
              : "rounded-bl-md border border-line bg-surface text-ink"
        )}
      >
        {isAgent ? (
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-emerald-700">
            Support agent
          </p>
        ) : null}
        <p className="whitespace-pre-wrap">{message.content}</p>
        {!isCustomer && message.meta?.toolResult ? (
          <p className="mt-2 flex items-center gap-1 text-[11px] text-muted">
            <Wrench className="h-3 w-3" />
            {message.meta.toolName ? `${message.meta.toolName} · ` : ""}
            {message.meta.toolResult}
          </p>
        ) : null}
        <p
          className={cn(
            "mt-1 text-[11px]",
            isCustomer ? "text-white/60" : "text-muted"
          )}
        >
          {message.timestamp}
        </p>
      </div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex gap-2.5">
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-soft text-accent">
        <Bot className="h-4 w-4" />
      </div>
      <div className="flex items-center gap-1 rounded-2xl rounded-bl-md border border-line bg-surface px-4 py-3">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent/50 [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent/50 [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent/50" />
      </div>
    </div>
  );
}
