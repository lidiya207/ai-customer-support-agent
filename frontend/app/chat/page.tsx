"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bot, History, LogOut, Plus, Send, Ticket, Trash2, UserRound } from "lucide-react";
import { RequireAuth } from "@/components/auth/route-guards";
import { useAuth } from "@/components/auth/auth-provider";
import { ChatMessage, TypingIndicator } from "@/components/chat/chat-message";
import { BrandMark } from "@/components/ui/brand-mark";
import { Button } from "@/components/ui/button";
import {
  checkAiStatus,
  deleteMyConversation,
  getMyConversation,
  listMyConversations,
  startMyNewConversation,
  streamChatMessage,
} from "@/lib/api";
import { initialChatMessages } from "@/lib/mock-data";
import type {
  ChatMessage as ChatMessageType,
  Conversation,
} from "@/lib/types";

const AI_ERROR_MESSAGE =
  "I'm having trouble connecting to the AI service right now. Please try again.";

const LAST_CONV_KEY = "ai_support_last_conversation_id";

const QUICK_PROMPTS = [
  "Where is my order #45231?",
  "How do I reset my password?",
  "Check my ticket status",
  "I want to talk to a human",
] as const;

function lastConversationStorageKey(userId: string) {
  return `${LAST_CONV_KEY}:${userId}`;
}

function ChatPageContent() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [messages, setMessages] = useState<ChatMessageType[]>(initialChatMessages);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [aiOnline, setAiOnline] = useState<boolean | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [historyItems, setHistoryItems] = useState<Conversation[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [agentStatus, setAgentStatus] = useState<string | null>(null);
  const [aiEnabled, setAiEnabled] = useState(true);
  const [conversationStatus, setConversationStatus] = useState<string | null>(
    null
  );
  const bottomRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const rememberConversation = useCallback(
    (id: string | null) => {
      setConversationId(id);
      if (!user?.id || typeof window === "undefined") return;
      const key = lastConversationStorageKey(user.id);
      if (id) {
        window.localStorage.setItem(key, id);
      } else {
        window.localStorage.removeItem(key);
      }
    },
    [user?.id]
  );

  const loadConversation = useCallback(
    async (id: string) => {
      const detail = await getMyConversation(id);
      rememberConversation(detail.id);
      setAiEnabled(detail.aiEnabled !== false);
      setConversationStatus(detail.status);
      if (detail.messages.length > 0) {
        setMessages(detail.messages);
      } else {
        setMessages(initialChatMessages);
      }
    },
    [rememberConversation]
  );

  const refreshHistory = useCallback(async () => {
    const items = await listMyConversations();
    setHistoryItems(items);
    return items;
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  useEffect(() => {
    let cancelled = false;

    async function loadAiStatus() {
      try {
        const status = await checkAiStatus();
        if (!cancelled) {
          setAiOnline(status.status === "online");
        }
      } catch (error) {
        console.error("Failed to check AI status:", error);
        if (!cancelled) {
          setAiOnline(false);
        }
      }
    }

    void loadAiStatus();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const userId = user?.id;
    if (!userId) return;

    let cancelled = false;

    async function hydrateChat() {
      setHistoryLoading(true);
      try {
        const items = await listMyConversations();
        if (cancelled) return;
        setHistoryItems(items);

        const savedId =
          typeof window !== "undefined"
            ? window.localStorage.getItem(lastConversationStorageKey(userId))
            : null;

        const preferred =
          (savedId && items.find((item) => item.id === savedId)) ||
          items.find((item) => item.status === "escalated") ||
          items.find(
            (item) => item.status === "active" || item.status === "waiting"
          ) ||
          items[0];

        if (preferred) {
          await loadConversation(preferred.id);
        } else {
          rememberConversation(null);
          setMessages(initialChatMessages);
        }
      } catch (error) {
        console.error("Failed to load conversation history:", error);
        if (!cancelled) {
          setHistoryItems([]);
          setMessages(initialChatMessages);
        }
      } finally {
        if (!cancelled) {
          setHistoryLoading(false);
        }
      }
    }

    void hydrateChat();
    return () => {
      cancelled = true;
    };
  }, [user?.id, loadConversation, rememberConversation]);

  useEffect(() => {
    function onClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  // While waiting for a human, poll so support-agent replies appear without refresh.
  useEffect(() => {
    if (!conversationId || isTyping) return;

    const waitingForHuman =
      aiEnabled === false || conversationStatus === "escalated";
    if (!waitingForHuman) return;

    const timer = window.setInterval(() => {
      void (async () => {
        try {
          const detail = await getMyConversation(conversationId);
          setAiEnabled(detail.aiEnabled !== false);
          setConversationStatus(detail.status);
          setMessages(detail.messages);
        } catch (error) {
          console.error("Failed to poll conversation:", error);
        }
      })();
    }, 3000);

    return () => window.clearInterval(timer);
  }, [conversationId, isTyping, aiEnabled, conversationStatus]);

  async function handleSend(e?: React.FormEvent, preset?: string) {
    e?.preventDefault();
    const trimmed = (preset ?? input).trim();
    if (!trimmed || isTyping) return;

    const userMessage: ChatMessageType = {
      id: `user-${Date.now()}`,
      role: "customer",
      content: trimmed,
      timestamp: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
    };
    const aiMessageId = `ai-${Date.now()}`;

    // Build history from prior turns BEFORE adding the new user bubble,
    // so follow-up questions still see the previous Q&A.
    const history = messages
      .filter((m) => m.role === "customer" || m.role === "ai")
      .filter((m) => m.id !== "welcome")
      .filter((m) => m.content.trim().length > 0)
      .slice(-12)
      .map((m) => ({
        role: (m.role === "customer" ? "user" : "assistant") as
          | "user"
          | "assistant",
        content: m.content,
      }));

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsTyping(true);
    setAgentStatus("Understanding your request…");

    try {

      let startedStreaming = false;

      const result = await streamChatMessage(
        trimmed,
        history,
        conversationId,
        {
          onMeta: (data) => {
            if (data.conversation_id) {
              rememberConversation(data.conversation_id);
            }
          },
          onStatus: (data) => {
            if (data.conversation_id) {
              rememberConversation(data.conversation_id);
            }
            const tools =
              data.tools_used && data.tools_used.length > 0
                ? ` · ${data.tools_used.join(", ")}`
                : "";
            setAgentStatus(
              `Intent: ${data.intent?.replace(/_/g, " ") ?? "thinking"}${tools}`
            );
          },
          onToken: (content) => {
            if (!startedStreaming) {
              startedStreaming = true;
              setIsTyping(false);
              setAgentStatus(null);
              setMessages((prev) => [
                ...prev,
                {
                  id: aiMessageId,
                  role: "ai",
                  content,
                  timestamp: new Date().toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  }),
                },
              ]);
              return;
            }
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? { ...msg, content: msg.content + content }
                  : msg
              )
            );
          },
          onDone: (done) => {
            if (done.conversation_id) {
              rememberConversation(done.conversation_id);
            }
            const isHandoff = done.intent === "human_handoff";
            if (done.escalated || isHandoff) {
              setAiEnabled(false);
              setConversationStatus("escalated");
            }

            // Already waiting for a human: keep the customer message only —
            // do not add another "System activity" bubble.
            if (isHandoff) {
              setMessages((prev) => {
                const withoutPartial = prev.filter((msg) => msg.id !== aiMessageId);
                const alreadyHasNotice = withoutPartial.some((msg) => {
                  const lower = msg.content.toLowerCase();
                  return (
                    msg.role === "system" ||
                    lower.includes("ai auto-replies") ||
                    lower.includes("support agent is handling") ||
                    lower.includes("escalated to a human")
                  );
                });
                if (alreadyHasNotice || aiEnabled === false || conversationStatus === "escalated") {
                  return withoutPartial;
                }
                return [
                  ...withoutPartial,
                  {
                    id: aiMessageId,
                    role: "system" as const,
                    content:
                      "A human support agent is handling this conversation. Keep this page open — their reply will appear here.",
                    timestamp: new Date().toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    }),
                  },
                ];
              });
              return;
            }

            const toolNote =
              !isHandoff && done.tools_used && done.tools_used.length > 0
                ? `Tools: ${done.tools_used.join(", ")}`
                : undefined;
            const escalateNote =
              !isHandoff && done.escalated
                ? `Escalated${done.ticket_id ? ` · ${done.ticket_id}` : ""}`
                : undefined;
            const metaText = [toolNote, escalateNote].filter(Boolean).join(" · ");
            const role = isHandoff ? ("system" as const) : ("ai" as const);

            setMessages((prev) => {
              const exists = prev.some((msg) => msg.id === aiMessageId);
              if (!exists) {
                return [
                  ...prev,
                  {
                    id: aiMessageId,
                    role,
                    content: done.response,
                    timestamp: new Date().toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    }),
                    meta: metaText
                      ? {
                          toolName: done.intent,
                          toolResult: metaText,
                        }
                      : undefined,
                  },
                ];
              }
              return prev.map((msg) =>
                msg.id === aiMessageId
                  ? {
                      ...msg,
                      role,
                      content: done.response || msg.content,
                      meta: metaText
                        ? {
                            toolName: done.intent,
                            toolResult: metaText,
                          }
                        : undefined,
                    }
                  : msg
              );
            });
          },
        }
      );

      if (result.conversation_id) {
        rememberConversation(result.conversation_id);
      }

      void refreshHistory().catch((error) => {
        console.error("Failed to refresh history:", error);
      });
    } catch (error) {
      console.error("Chat request failed:", error);
      const detail =
        error instanceof Error && error.message.trim()
          ? error.message
          : AI_ERROR_MESSAGE;
      setMessages((prev) => {
        const withoutPartial = prev.filter((msg) => msg.id !== aiMessageId);
        return [
          ...withoutPartial,
          {
            id: `ai-error-${Date.now()}`,
            role: "ai",
            content: detail.includes("timed out")
              ? "The local AI model is still loading or busy. Please wait a moment and try again."
              : detail || AI_ERROR_MESSAGE,
            timestamp: new Date().toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            }),
          },
        ];
      });
    } finally {
      setIsTyping(false);
      setAgentStatus(null);
    }
  }

  async function handleNewConversation() {
    try {
      await startMyNewConversation();
    } catch (error) {
      console.error("Failed to start new conversation:", error);
    }
    rememberConversation(null);
    setMessages(initialChatMessages);
    setAiEnabled(true);
    setConversationStatus(null);
    setInput("");
    setShowHistory(false);
    void refreshHistory().catch((error) => {
      console.error("Failed to refresh history:", error);
    });
  }

  async function handleSelectHistory(id: string) {
    try {
      await loadConversation(id);
      setShowHistory(false);
    } catch (error) {
      console.error("Failed to open conversation:", error);
    }
  }

  async function handleDeleteHistory(id: string) {
    try {
      await deleteMyConversation(id);
      const remaining = historyItems.filter((item) => item.id !== id);
      setHistoryItems(remaining);

      if (conversationId === id) {
        const next = remaining[0];
        if (next) {
          await loadConversation(next.id);
        } else {
          rememberConversation(null);
          setMessages(initialChatMessages);
        }
      }
    } catch (error) {
      console.error("Failed to delete conversation:", error);
    }
  }

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  const visibleMessages = useMemo(() => {
    const isHandoffNotice = (content: string) => {
      const lower = content.toLowerCase();
      return (
        lower.includes("ai auto-replies") ||
        lower.includes("support agent is handling") ||
        lower.includes("escalated to a human") ||
        lower.includes("message received") ||
        lower.includes("waiting for the support agent") ||
        lower.includes("delivered to the support agent") ||
        lower.includes("they will reply here shortly")
      );
    };
    const result: ChatMessageType[] = [];
    let sawHandoffSystem = false;
    for (const message of messages) {
      // Hide repeated handoff notices (system OR ai bubbles from older builds).
      if (
        (message.role === "system" || message.role === "ai") &&
        isHandoffNotice(message.content)
      ) {
        if (sawHandoffSystem) continue;
        sawHandoffSystem = true;
        // Prefer a single clean system notice in the UI.
        result.push({
          ...message,
          role: "system",
          content:
            "A human support agent is handling this conversation. Keep this page open — their reply will appear here.",
          meta: undefined,
        });
        continue;
      }
      result.push(message);
    }
    return result;
  }, [messages]);

  const firstName = user?.name?.split(" ")[0] ?? "there";
  const statusLabel =
    aiOnline === null ? "Checking…" : aiOnline ? "AI Online" : "AI Offline";
  const statusColor =
    aiOnline === true
      ? "text-emerald-600"
      : aiOnline === false
        ? "text-red-500"
        : "text-muted";
  const statusDot =
    aiOnline === true
      ? "bg-emerald-500"
      : aiOnline === false
        ? "bg-red-500"
        : "bg-line";

  return (
    <div className="flex h-screen flex-col bg-canvas">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between gap-3 px-4">
          <Link href="/" className="flex min-w-0 items-center gap-2.5">
            <BrandMark showWordmark={false} />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-ink">AI Support</p>
              <p className={`flex items-center gap-1.5 text-xs ${statusColor}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${statusDot}`} />
                {statusLabel}
              </p>
            </div>
          </Link>

          <div className="flex shrink-0 items-center gap-1.5">
            <span className="mr-1 hidden text-sm text-muted sm:inline">
              Hi, <span className="font-medium text-ink">{firstName}</span>
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void handleNewConversation()}
              type="button"
            >
              <Plus className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">New</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              type="button"
              onClick={() => setShowHistory((v) => !v)}
            >
              <History className="h-3.5 w-3.5" />
            </Button>

            <div className="relative" ref={menuRef}>
              <button
                type="button"
                onClick={() => setMenuOpen((v) => !v)}
                className="flex h-8 w-8 items-center justify-center rounded-full bg-brand text-xs font-semibold text-white"
                aria-label="User menu"
              >
                {(user?.name?.[0] ?? "U").toUpperCase()}
              </button>
              {menuOpen ? (
                <div className="absolute right-0 z-50 mt-2 w-48 rounded-xl border border-line bg-surface py-1.5 shadow-lg">
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm text-muted hover:bg-canvas hover:text-ink"
                    onClick={() => {
                      setMenuOpen(false);
                      router.push("/profile");
                    }}
                  >
                    <UserRound className="h-4 w-4" />
                    Profile
                  </button>
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm text-muted hover:bg-canvas hover:text-ink"
                    onClick={() => {
                      setMenuOpen(false);
                      router.push("/tickets");
                    }}
                  >
                    <Ticket className="h-4 w-4" />
                    My tickets
                  </button>
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm text-muted hover:bg-canvas hover:text-ink"
                    onClick={() => void handleLogout()}
                  >
                    <LogOut className="h-4 w-4" />
                    Logout
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </header>

      {showHistory ? (
        <div className="border-b border-line bg-surface">
          <div className="mx-auto max-w-3xl space-y-1.5 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">
              History
            </p>
            {historyLoading ? (
              <p className="text-sm text-muted">Loading…</p>
            ) : historyItems.length === 0 ? (
              <p className="text-sm text-muted">No conversations yet.</p>
            ) : (
              historyItems.map((item) => (
                <div
                  key={item.id}
                  className={`flex items-center gap-2 rounded-lg border px-3 py-2 ${
                    item.id === conversationId
                      ? "border-accent bg-accent-soft text-ink"
                      : "border-line text-ink"
                  }`}
                >
                  <button
                    type="button"
                    className="min-w-0 flex-1 text-left text-sm hover:opacity-80"
                    onClick={() => void handleSelectHistory(item.id)}
                  >
                    <span className="block truncate font-medium">
                      {item.topic || "Support"}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-muted">
                      {item.lastMessage || item.status}
                    </span>
                  </button>
                  <button
                    type="button"
                    aria-label={`Delete ${item.topic || "conversation"}`}
                    className="shrink-0 rounded-md p-1.5 text-muted transition hover:bg-red-50 hover:text-red-600"
                    onClick={(e) => {
                      e.stopPropagation();
                      void handleDeleteHistory(item.id);
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      ) : null}

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-3xl flex-col gap-3.5 px-4 py-6">
          {aiEnabled === false || conversationStatus === "escalated" ? (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              Waiting for a human support agent. Keep this page open — their
              reply will appear here automatically.
            </div>
          ) : null}
          {messages.length === 0 ? (
            <div className="flex flex-1 flex-col items-center justify-center py-20 text-center">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-accent-soft text-accent">
                <Bot className="h-6 w-6" />
              </div>
              <p className="text-base font-semibold text-ink">
                How can we help?
              </p>
              <p className="mt-1 text-sm text-muted">
                Ask about orders, billing, or your account.
              </p>
            </div>
          ) : (
            visibleMessages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))
          )}
          {isTyping ? (
            <div className="space-y-2">
              <TypingIndicator />
              {agentStatus ? (
                <p className="pl-11 text-xs text-muted">{agentStatus}</p>
              ) : null}
            </div>
          ) : null}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="border-t border-line bg-surface">
        <div className="mx-auto flex max-w-3xl gap-2 overflow-x-auto px-4 pt-3">
          {QUICK_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              disabled={isTyping}
              onClick={() => void handleSend(undefined, prompt)}
              className="shrink-0 rounded-full border border-line bg-canvas px-3 py-1.5 text-xs text-muted transition hover:border-accent hover:bg-accent-soft hover:text-accent disabled:opacity-50"
            >
              {prompt}
            </button>
          ))}
        </div>
        <form
          onSubmit={(e) => void handleSend(e)}
          className="mx-auto flex max-w-3xl items-end gap-2 px-4 py-3"
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void handleSend();
              }
            }}
            placeholder="Type your message..."
            rows={1}
            disabled={isTyping}
            className="max-h-32 min-h-11 flex-1 resize-none rounded-xl border border-line bg-canvas px-4 py-3 text-sm outline-none transition focus:border-accent focus:bg-surface focus:ring-2 focus:ring-accent/15 disabled:opacity-60"
          />
          <Button type="submit" disabled={!input.trim() || isTyping} className="h-11 px-4">
            <Send className="h-4 w-4" />
            <span className="hidden sm:inline">Send</span>
          </Button>
        </form>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <RequireAuth>
      <ChatPageContent />
    </RequireAuth>
  );
}
