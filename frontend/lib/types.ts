export type ConversationStatus =
  | "active"
  | "resolved"
  | "escalated"
  | "waiting"
  | "closed";

export type TicketStatus = "open" | "in_progress" | "waiting" | "resolved";

export type TicketPriority = "low" | "medium" | "high" | "critical";

export type AgentRunStatus = "success" | "escalated" | "failed";

export type MessageRole = "customer" | "ai" | "system" | "support_agent";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  meta?: {
    toolName?: string;
    toolResult?: string;
  };
}

export interface Conversation {
  id: string;
  customer: string;
  email: string;
  topic: string;
  lastMessage: string;
  intent: string;
  confidence: number;
  status: ConversationStatus;
  assignedAgent?: string | null;
  aiEnabled?: boolean;
  updatedAt: string;
  createdAt: string;
}

export interface ConversationDetail extends Conversation {
  messages: ChatMessage[];
  assignedAgent?: string | null;
  aiEnabled?: boolean;
  agentDetails: {
    detectedIntent: string;
    confidence: number;
    agentStatus: string;
    knowledgeUsed: string[];
    toolsUsed: string[];
    timeline: AgentTimelineStep[];
  };
}

export interface AgentTimelineStep {
  id: string;
  label: string;
  description?: string;
  timestamp: string;
}

export interface Ticket {
  id: string;
  customer: string;
  category: string;
  priority: TicketPriority;
  assignedTo: string;
  status: TicketStatus;
  createdAt: string;
  title?: string;
  conversationId?: string | null;
}

export interface AppSettings {
  system_prompt: string;
  model_override: string;
  temperature: number;
  confidence_threshold: number;
  escalate_refunds: boolean;
  escalate_complaints: boolean;
  max_failed_tools: number;
  workspace_name: string;
  support_email: string;
}

export interface KnowledgeDocument {
  id: string;
  name: string;
  type: "PDF" | "DOCX" | "TXT";
  chunks: number;
  status: "indexed" | "processing" | "failed";
  uploadedAt: string;
}

export interface AgentRun {
  id: string;
  input: string;
  intent: string;
  action: string;
  tool: string;
  confidence: number;
  latency: string;
  status: AgentRunStatus;
  details: {
    userInput: string;
    detectedIntent: string;
    agentDecision: string;
    knowledgeRetrieved: string;
    toolCalls: string;
    toolInput: string;
    toolOutput: string;
    finalResponse: string;
    executionTime: string;
  };
}

export interface DashboardStats {
  totalConversations: number;
  totalConversationsChange: string;
  aiResolved: number;
  resolutionRate: string;
  escalated: number;
  escalationRate: string;
  openTickets: number;
  highPriority: number;
}

export interface AppNotification {
  id: string;
  type: string;
  title: string;
  body: string;
  conversationId: string | null;
  ticketId: string | null;
  isRead: boolean;
  createdAt: string | null;
}

export interface ChartPoint {
  label: string;
  value: number;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
}

export interface ChatResponse {
  response: string;
  model?: string;
  intent?: string;
  confidence?: number;
  tools_used?: string[];
  sources?: Array<{
    document_id?: string;
    title?: string;
    similarity?: number;
  }>;
  escalated?: boolean;
  ticket_id?: string | null;
  conversation_id?: string | null;
}
