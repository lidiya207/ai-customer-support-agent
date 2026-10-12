import type { AuthUser, TokenResponse } from "./auth";
import { clearAuthSession, getStoredToken, setAuthSession } from "./auth";
import type {
  AgentRun,
  AppNotification,
  AppSettings,
  ChatResponse,
  Conversation,
  ConversationDetail,
  DashboardStats,
  KnowledgeDocument,
  Ticket,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export function getApiUrl() {
  return API_URL;
}

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown };
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((item) => {
          if (typeof item === "object" && item && "msg" in item) {
            return String((item as { msg: string }).msg);
          }
          return JSON.stringify(item);
        })
        .join(", ");
    }
  } catch {
    // fall through
  }
  const text = await response.text().catch(() => "");
  return text || `Request failed with status ${response.status}`;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  authenticated = false
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };

  if (authenticated) {
    const token = getStoredToken();
    if (!token) {
      throw new ApiError(401, "Not authenticated.");
    }
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const detail = await parseErrorDetail(response);
    // Stale/expired JWT — clear local session so the UI recovers cleanly.
    if (response.status === 401 && authenticated) {
      clearAuthSession();
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function register(input: {
  name: string;
  email: string;
  password: string;
}): Promise<TokenResponse> {
  const data = await request<TokenResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(input),
  });
  setAuthSession(data.access_token, data.user);
  return data;
}

export async function login(input: {
  email: string;
  password: string;
}): Promise<TokenResponse> {
  const data = await request<TokenResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
  setAuthSession(data.access_token, data.user);
  return data;
}

export async function logout(): Promise<void> {
  try {
    await request<{ detail: string }>(
      "/api/auth/logout",
      { method: "POST" },
      true
    );
  } catch {
    // Always clear local session even if the API call fails.
  } finally {
    clearAuthSession();
  }
}

export async function getCurrentUser(): Promise<AuthUser> {
  return request<AuthUser>("/api/auth/me", {}, true);
}

export async function updateProfile(input: {
  name: string;
  email: string;
}): Promise<AuthUser> {
  const user = await request<AuthUser>(
    "/api/auth/me",
    {
      method: "PATCH",
      body: JSON.stringify(input),
    },
    true
  );
  const token = getStoredToken();
  if (token) {
    setAuthSession(token, user);
  }
  return user;
}

export async function changePassword(input: {
  current_password: string;
  new_password: string;
}): Promise<{ detail: string }> {
  return request<{ detail: string }>(
    "/api/auth/change-password",
    {
      method: "POST",
      body: JSON.stringify(input),
    },
    true
  );
}

export interface AdminUser extends AuthUser {
  created_at: string;
}

/**
 * List registered users for the admin dashboard.
 * GET /api/admin/users?role=customer
 */
export async function listAdminUsers(role?: AuthUser["role"]): Promise<AdminUser[]> {
  const query = role ? `?role=${encodeURIComponent(role)}` : "";
  return request<AdminUser[]>(`/api/admin/users${query}`, {}, true);
}

/**
 * Send a chat message to the agentic support backend.
 * POST /api/chat → { response, intent, tools_used, escalated, ... }
 */
export async function sendChatMessage(
  message: string,
  history: Array<{ role: "user" | "assistant"; content: string }> = [],
  conversationId?: string | null
): Promise<ChatResponse> {
  return request<ChatResponse>(
    "/api/chat",
    {
      method: "POST",
      body: JSON.stringify({
        message,
        history,
        conversation_id: conversationId || undefined,
      }),
    },
    true
  );
}

export interface ChatStreamHandlers {
  onMeta?: (data: { conversation_id?: string; status?: string }) => void;
  onStatus?: (data: {
    intent?: string;
    confidence?: number;
    tools_used?: string[];
    escalated?: boolean;
    ticket_id?: string | null;
    model?: string;
    conversation_id?: string;
  }) => void;
  onToken?: (content: string) => void;
  onDone?: (data: ChatResponse) => void;
  onError?: (detail: string) => void;
}

/**
 * Stream an agentic reply via SSE.
 * POST /api/chat/stream → events: meta, status, token, done, error
 */
export async function streamChatMessage(
  message: string,
  history: Array<{ role: "user" | "assistant"; content: string }> = [],
  conversationId: string | null | undefined,
  handlers: ChatStreamHandlers
): Promise<ChatResponse> {
  const token = getStoredToken();
  if (!token) {
    throw new ApiError(401, "Not authenticated.");
  }

  const response = await fetch(`${API_URL}/api/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      Accept: "text/event-stream",
    },
    body: JSON.stringify({
      message,
      history,
      conversation_id: conversationId || undefined,
    }),
  });

  if (!response.ok) {
    const detail = await parseErrorDetail(response);
    if (response.status === 401) {
      clearAuthSession();
    }
    throw new ApiError(response.status, detail);
  }

  if (!response.body) {
    throw new ApiError(502, "No stream body received from the server.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult: ChatResponse | null = null;
  let streamError: string | null = null;

  const dispatch = (eventName: string, rawData: string) => {
    let data: Record<string, unknown> = {};
    try {
      data = JSON.parse(rawData) as Record<string, unknown>;
    } catch {
      return;
    }

    if (eventName === "meta") {
      handlers.onMeta?.(data as { conversation_id?: string; status?: string });
    } else if (eventName === "status") {
      handlers.onStatus?.(
        data as {
          intent?: string;
          confidence?: number;
          tools_used?: string[];
          escalated?: boolean;
          ticket_id?: string | null;
          model?: string;
          conversation_id?: string;
        }
      );
    } else if (eventName === "token") {
      const content = typeof data.content === "string" ? data.content : "";
      if (content) handlers.onToken?.(content);
    } else if (eventName === "done") {
      finalResult = data as unknown as ChatResponse;
      handlers.onDone?.(finalResult);
    } else if (eventName === "error") {
      streamError =
        typeof data.detail === "string" ? data.detail : "Stream failed.";
      handlers.onError?.(streamError);
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let separatorIndex = buffer.indexOf("\n\n");
    while (separatorIndex !== -1) {
      const chunk = buffer.slice(0, separatorIndex);
      buffer = buffer.slice(separatorIndex + 2);

      let eventName = "message";
      const dataLines: string[] = [];
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).trim());
        }
      }
      if (dataLines.length > 0) {
        dispatch(eventName, dataLines.join("\n"));
      }

      separatorIndex = buffer.indexOf("\n\n");
    }
  }

  if (streamError) {
    throw new ApiError(503, streamError);
  }
  if (!finalResult) {
    throw new ApiError(502, "Stream ended without a complete response.");
  }
  return finalResult;
}

export async function listConversations(): Promise<Conversation[]> {
  return request<Conversation[]>("/api/conversations", {}, true);
}

export async function getConversation(
  id: string
): Promise<ConversationDetail> {
  return request<ConversationDetail>(`/api/conversations/${id}`, {}, true);
}

/** Customer: list my own conversations (survives logout). */
export async function listMyConversations(): Promise<Conversation[]> {
  return request<Conversation[]>("/api/conversations/me", {}, true);
}

/** Customer: load one of my conversations with messages. */
export async function getMyConversation(
  id: string
): Promise<ConversationDetail> {
  return request<ConversationDetail>(`/api/conversations/me/${id}`, {}, true);
}

/** Customer: close active threads so the next message starts a new conversation. */
export async function startMyNewConversation(): Promise<{
  detail: string;
  closed: number;
}> {
  return request<{ detail: string; closed: number }>(
    "/api/conversations/me/new",
    { method: "POST" },
    true
  );
}

/** Customer: permanently delete one of my conversations. */
export async function deleteMyConversation(
  id: string
): Promise<{ detail: string }> {
  return request<{ detail: string }>(
    `/api/conversations/me/${id}`,
    { method: "DELETE" },
    true
  );
}

export async function listTickets(): Promise<Ticket[]> {
  return request<Ticket[]>("/api/tickets", {}, true);
}

export async function listMyTickets(): Promise<Ticket[]> {
  return request<Ticket[]>("/api/tickets/me", {}, true);
}

export async function updateTicket(
  ticketCode: string,
  updates: { status?: string; assigned_agent?: string }
): Promise<{ ok: boolean; id: string; status: string }> {
  return request(`/api/tickets/${encodeURIComponent(ticketCode)}`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  }, true);
}

export async function claimConversation(
  conversationId: string
): Promise<ConversationDetail> {
  return request<ConversationDetail>(
    `/api/conversations/${conversationId}/claim`,
    { method: "POST" },
    true
  );
}

export async function replyToConversation(
  conversationId: string,
  content: string
): Promise<ConversationDetail> {
  return request<ConversationDetail>(
    `/api/conversations/${conversationId}/messages`,
    {
      method: "POST",
      body: JSON.stringify({ content }),
    },
    true
  );
}

export async function updateConversation(
  conversationId: string,
  updates: { status?: string; ai_enabled?: boolean }
): Promise<ConversationDetail> {
  return request<ConversationDetail>(
    `/api/conversations/${conversationId}`,
    {
      method: "PATCH",
      body: JSON.stringify(updates),
    },
    true
  );
}

export async function getSettings(): Promise<AppSettings> {
  return request<AppSettings>("/api/settings", {}, true);
}

export async function saveSettings(
  updates: Partial<AppSettings>
): Promise<AppSettings> {
  return request<AppSettings>(
    "/api/settings",
    {
      method: "PUT",
      body: JSON.stringify(updates),
    },
    true
  );
}

export async function listKnowledgeDocuments(): Promise<KnowledgeDocument[]> {
  return request<KnowledgeDocument[]>("/api/knowledge/documents", {}, true);
}

export async function uploadKnowledgeDocument(
  file: File,
  category = "general"
): Promise<KnowledgeDocument> {
  const form = new FormData();
  form.append("file", file);
  form.append("category", category);

  const token = getStoredToken();
  const response = await fetch(`${API_URL}/api/knowledge/documents`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }
  return response.json() as Promise<KnowledgeDocument>;
}

export async function listAgentRuns(): Promise<AgentRun[]> {
  return request<AgentRun[]>("/api/agent-runs", {}, true);
}

export async function getAnalyticsOverview(): Promise<DashboardStats> {
  return request<DashboardStats>("/api/analytics/overview", {}, true);
}

export async function listNotifications(): Promise<AppNotification[]> {
  return request<AppNotification[]>("/api/notifications", {}, true);
}

export async function getUnreadNotificationCount(): Promise<{ count: number }> {
  return request<{ count: number }>("/api/notifications/unread-count", {}, true);
}

export async function markNotificationRead(
  id: string
): Promise<AppNotification> {
  return request<AppNotification>(
    `/api/notifications/${encodeURIComponent(id)}/read`,
    { method: "POST" },
    true
  );
}

export async function markAllNotificationsRead(): Promise<{ updated: number }> {
  return request<{ updated: number }>(
    "/api/notifications/read-all",
    { method: "POST" },
    true
  );
}

export interface AiStatus {
  status: "online" | "offline";
  provider: string;
  model?: string;
}

/**
 * Check whether the Ollama-backed AI service is reachable.
 * GET /api/ai/status
 */
export async function checkAiStatus(): Promise<AiStatus> {
  return request<AiStatus>("/api/ai/status");
}

/**
 * Health check against the FastAPI root.
 */
export async function checkApiHealth(): Promise<{ message: string }> {
  return request<{ message: string }>("/");
}
