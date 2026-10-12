import type {
  AgentRun,
  ChartPoint,
  Conversation,
  ConversationDetail,
  DashboardStats,
  KnowledgeDocument,
  Ticket,
} from "./types";

/** Mock data — replace with API calls when FastAPI endpoints are ready. */

export const dashboardStats: DashboardStats = {
  totalConversations: 1284,
  totalConversationsChange: "+12% this month",
  aiResolved: 986,
  resolutionRate: "76.8% resolution rate",
  escalated: 184,
  escalationRate: "14.3% escalation rate",
  openTickets: 37,
  highPriority: 8,
};

export const conversationActivity: ChartPoint[] = [
  { label: "Mon", value: 42 },
  { label: "Tue", value: 58 },
  { label: "Wed", value: 51 },
  { label: "Thu", value: 73 },
  { label: "Fri", value: 66 },
  { label: "Sat", value: 38 },
  { label: "Sun", value: 45 },
];

export const recentConversations: Conversation[] = [
  {
    id: "conv-001",
    customer: "Sarah Johnson",
    email: "sarah.johnson@email.com",
    topic: "Subscription cancellation",
    lastMessage: "Can I cancel my plan?",
    intent: "subscription_question",
    confidence: 92,
    status: "resolved",
    updatedAt: "2 min ago",
    createdAt: "Oct 6, 2026 2:14 PM",
  },
  {
    id: "conv-002",
    customer: "Daniel Smith",
    email: "daniel.smith@email.com",
    topic: "Order delivery issue",
    lastMessage: "Where is my order?",
    intent: "order_status",
    confidence: 87,
    status: "resolved",
    updatedAt: "8 min ago",
    createdAt: "Oct 6, 2026 2:08 PM",
  },
  {
    id: "conv-003",
    customer: "Emily Brown",
    email: "emily.brown@email.com",
    topic: "Duplicate payment",
    lastMessage: "I was charged twice.",
    intent: "billing_dispute",
    confidence: 64,
    status: "escalated",
    updatedAt: "14 min ago",
    createdAt: "Oct 6, 2026 2:02 PM",
  },
  {
    id: "conv-004",
    customer: "Michael Lee",
    email: "michael.lee@email.com",
    topic: "Password reset",
    lastMessage: "How do I reset my password?",
    intent: "technical_support",
    confidence: 95,
    status: "resolved",
    updatedAt: "20 min ago",
    createdAt: "Oct 6, 2026 1:56 PM",
  },
  {
    id: "conv-005",
    customer: "James Wilson",
    email: "james.wilson@email.com",
    topic: "Product availability",
    lastMessage: "Is the Pro plan still available?",
    intent: "product_inquiry",
    confidence: 88,
    status: "active",
    updatedAt: "25 min ago",
    createdAt: "Oct 6, 2026 1:51 PM",
  },
  {
    id: "conv-006",
    customer: "Olivia Martinez",
    email: "olivia.m@email.com",
    topic: "Invoice request",
    lastMessage: "Can you resend my invoice?",
    intent: "billing_request",
    confidence: 91,
    status: "waiting",
    updatedAt: "32 min ago",
    createdAt: "Oct 6, 2026 1:44 PM",
  },
];

export const conversationDetails: Record<string, ConversationDetail> = {
  "conv-001": {
    ...recentConversations[0],
    messages: [
      {
        id: "m1",
        role: "customer",
        content: "Can I cancel my plan?",
        timestamp: "2:14 PM",
      },
      {
        id: "m2",
        role: "ai",
        content:
          "Yes, you can cancel anytime. Would you like me to walk you through the steps or create a cancellation ticket?",
        timestamp: "2:14 PM",
      },
      {
        id: "m3",
        role: "customer",
        content: "Just the steps is fine.",
        timestamp: "2:15 PM",
      },
      {
        id: "m4",
        role: "ai",
        content:
          "Go to Settings → Billing → Cancel Subscription. Your access remains until the end of the billing period.",
        timestamp: "2:15 PM",
      },
    ],
    agentDetails: {
      detectedIntent: "subscription_question",
      confidence: 92,
      agentStatus: "Resolved by AI",
      knowledgeUsed: ["Subscription Policy.pdf"],
      toolsUsed: [],
      timeline: [
        {
          id: "t1",
          label: "Customer message received",
          timestamp: "2:14:02 PM",
        },
        {
          id: "t2",
          label: "Intent detected",
          description: "subscription_question",
          timestamp: "2:14:03 PM",
        },
        {
          id: "t3",
          label: "Knowledge retrieved",
          description: "Subscription Policy.pdf",
          timestamp: "2:14:04 PM",
        },
        {
          id: "t4",
          label: "Response generated",
          timestamp: "2:14:05 PM",
        },
      ],
    },
  },
  "conv-002": {
    ...recentConversations[1],
    messages: [
      {
        id: "m1",
        role: "customer",
        content: "Where is order ORD-1001?",
        timestamp: "2:08 PM",
      },
      {
        id: "m2",
        role: "ai",
        content: "Let me check that order for you.",
        timestamp: "2:08 PM",
      },
      {
        id: "m3",
        role: "system",
        content: "Tool Called: get_order_status",
        timestamp: "2:08 PM",
        meta: {
          toolName: "get_order_status",
          toolResult: "Order shipped\nExpected delivery: Oct 9",
        },
      },
      {
        id: "m4",
        role: "ai",
        content:
          "Your order has shipped and should arrive on October 9.",
        timestamp: "2:08 PM",
      },
    ],
    agentDetails: {
      detectedIntent: "order_status",
      confidence: 91,
      agentStatus: "Resolved by AI",
      knowledgeUsed: [],
      toolsUsed: ["get_order_status"],
      timeline: [
        {
          id: "t1",
          label: "Customer message received",
          timestamp: "2:08:01 PM",
        },
        {
          id: "t2",
          label: "Intent detected",
          description: "order_status (91%)",
          timestamp: "2:08:02 PM",
        },
        {
          id: "t3",
          label: "Tool selected",
          description: "get_order_status",
          timestamp: "2:08:03 PM",
        },
        {
          id: "t4",
          label: "Tool executed",
          description: "Order shipped — Expected delivery: Oct 9",
          timestamp: "2:08:04 PM",
        },
        {
          id: "t5",
          label: "Response generated",
          timestamp: "2:08:05 PM",
        },
      ],
    },
  },
};

export function getConversationDetail(id: string): ConversationDetail {
  if (conversationDetails[id]) {
    return conversationDetails[id];
  }

  const base =
    recentConversations.find((c) => c.id === id) ?? recentConversations[1];

  return {
    ...base,
    id,
    messages: conversationDetails["conv-002"].messages,
    agentDetails: conversationDetails["conv-002"].agentDetails,
  };
}

export const tickets: Ticket[] = [
  {
    id: "TCK-1042",
    customer: "Emily Brown",
    category: "Billing",
    priority: "high",
    assignedTo: "Sarah Agent",
    status: "in_progress",
    createdAt: "14m",
  },
  {
    id: "TCK-1041",
    customer: "James Wilson",
    category: "Technical",
    priority: "medium",
    assignedTo: "Unassigned",
    status: "open",
    createdAt: "32m",
  },
  {
    id: "TCK-1040",
    customer: "Olivia Martinez",
    category: "Account",
    priority: "low",
    assignedTo: "Mike Agent",
    status: "waiting",
    createdAt: "1h",
  },
  {
    id: "TCK-1039",
    customer: "Chris Adams",
    category: "Billing",
    priority: "critical",
    assignedTo: "Sarah Agent",
    status: "open",
    createdAt: "2h",
  },
  {
    id: "TCK-1038",
    customer: "Daniel Smith",
    category: "Shipping",
    priority: "medium",
    assignedTo: "Lisa Agent",
    status: "resolved",
    createdAt: "3h",
  },
];

export const ticketStats = {
  open: 37,
  inProgress: 12,
  waiting: 8,
  resolvedToday: 24,
};

export const knowledgeDocuments: KnowledgeDocument[] = [
  {
    id: "doc-1",
    name: "Subscription Policy.pdf",
    type: "PDF",
    chunks: 86,
    status: "indexed",
    uploadedAt: "Oct 5",
  },
  {
    id: "doc-2",
    name: "Refund Policy.pdf",
    type: "PDF",
    chunks: 42,
    status: "indexed",
    uploadedAt: "Oct 4",
  },
  {
    id: "doc-3",
    name: "Technical Support Guide.pdf",
    type: "PDF",
    chunks: 194,
    status: "indexed",
    uploadedAt: "Oct 3",
  },
  {
    id: "doc-4",
    name: "Shipping FAQ.docx",
    type: "DOCX",
    chunks: 28,
    status: "indexed",
    uploadedAt: "Oct 2",
  },
  {
    id: "doc-5",
    name: "Account Security.txt",
    type: "TXT",
    chunks: 15,
    status: "processing",
    uploadedAt: "Oct 6",
  },
];

export const knowledgeStats = {
  documents: 24,
  chunks: 1842,
  indexed: 24,
  processing: 0,
};

export const agentRuns: AgentRun[] = [
  {
    id: "run-001",
    input: "Where is ORD-1001?",
    intent: "order_status",
    action: "Tool Call",
    tool: "get_order_status",
    confidence: 94,
    latency: "1.4s",
    status: "success",
    details: {
      userInput: "Where is ORD-1001?",
      detectedIntent: "order_status",
      agentDecision:
        "Customer is asking about order tracking. Use get_order_status tool with order ID ORD-1001.",
      knowledgeRetrieved: "None",
      toolCalls: "get_order_status",
      toolInput: '{ "order_id": "ORD-1001" }',
      toolOutput:
        '{ "status": "shipped", "expected_delivery": "2026-10-09", "carrier": "UPS" }',
      finalResponse:
        "Your order has shipped and should arrive on October 9.",
      executionTime: "1.4s",
    },
  },
  {
    id: "run-002",
    input: "I want a refund",
    intent: "refund_request",
    action: "Escalation",
    tool: "create_ticket",
    confidence: 71,
    latency: "1.7s",
    status: "escalated",
    details: {
      userInput: "I want a refund",
      detectedIntent: "refund_request",
      agentDecision:
        "Refund requests require human review per escalation rules. Create a support ticket and escalate.",
      knowledgeRetrieved: "Refund Policy.pdf — Section 3",
      toolCalls: "create_ticket",
      toolInput:
        '{ "category": "Billing", "priority": "high", "reason": "refund_request" }',
      toolOutput: '{ "ticket_id": "TCK-1042", "status": "open" }',
      finalResponse:
        "I've created ticket TCK-1042 and connected you with a support agent who can process your refund.",
      executionTime: "1.7s",
    },
  },
  {
    id: "run-003",
    input: "How do I reset my password?",
    intent: "technical_support",
    action: "Knowledge Search",
    tool: "search_knowledge_base",
    confidence: 96,
    latency: "1.2s",
    status: "success",
    details: {
      userInput: "How do I reset my password?",
      detectedIntent: "technical_support",
      agentDecision:
        "Password reset is covered in the knowledge base. Search and return step-by-step instructions.",
      knowledgeRetrieved: "Account Security.txt — Password Reset",
      toolCalls: "search_knowledge_base",
      toolInput: '{ "query": "password reset steps" }',
      toolOutput:
        "Go to Login → Forgot Password → enter email → follow the reset link.",
      finalResponse:
        "You can reset your password from the login page by clicking Forgot Password and following the email link.",
      executionTime: "1.2s",
    },
  },
  {
    id: "run-004",
    input: "What's included in the Pro plan?",
    intent: "product_inquiry",
    action: "Knowledge Search",
    tool: "search_knowledge_base",
    confidence: 89,
    latency: "1.5s",
    status: "success",
    details: {
      userInput: "What's included in the Pro plan?",
      detectedIntent: "product_inquiry",
      agentDecision: "Retrieve plan comparison from knowledge base.",
      knowledgeRetrieved: "Subscription Policy.pdf — Plans",
      toolCalls: "search_knowledge_base",
      toolInput: '{ "query": "Pro plan features" }',
      toolOutput:
        "Pro includes unlimited seats, priority support, and advanced analytics.",
      finalResponse:
        "The Pro plan includes unlimited seats, priority support, and advanced analytics.",
      executionTime: "1.5s",
    },
  },
];

export const agentStats = {
  agentRuns: 2481,
  toolCalls: 1208,
  averageLatency: "1.8s",
  successfulRuns: "97.4%",
};

export const analyticsData = {
  aiResolutionRate: "76.8%",
  escalationRate: "14.3%",
  averageResponseTime: "1.8 sec",
  customerSatisfaction: "4.6 / 5",
  conversationVolume: conversationActivity,
  aiVsHuman: [
    { label: "AI Resolved", value: 986 },
    { label: "Human Resolved", value: 184 },
    { label: "Pending", value: 114 },
  ],
  topTopics: [
    { label: "Order Status", value: 312 },
    { label: "Billing", value: 248 },
    { label: "Account", value: 186 },
    { label: "Technical", value: 154 },
    { label: "Subscriptions", value: 128 },
  ],
  escalationReasons: [
    { label: "Refund Dispute", value: 42 },
    { label: "Complex Billing", value: 38 },
    { label: "Angry Customer", value: 31 },
    { label: "Legal Request", value: 18 },
    { label: "Low Confidence", value: 55 },
  ],
};

export const initialChatMessages = [
  {
    id: "welcome",
    role: "ai" as const,
    content:
      "Hello! I'm your AI support assistant.\nHow can I help you today?",
    timestamp: new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    }),
  },
];
