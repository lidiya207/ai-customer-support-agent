# AI Customer Support Agent — SRS (List Form)

**Version:** 1.0  
**Type:** Agentic AI / SaaS Customer Support Platform  
**Stack:** Python, FastAPI, OpenAI/Claude (or Ollama), PostgreSQL + pgvector, Redis, Next.js, React, TypeScript, Docker

---

## 1. Objectives

1. Reduce repetitive customer support work
2. Give instant answers to common questions
3. Retrieve accurate answers from a knowledge base (RAG)
4. Let the AI call external tools / APIs
5. Auto-create support tickets when needed
6. Escalate complex or sensitive cases to humans
7. Keep conversation memory
8. Give admins visibility into AI decisions
9. Track conversations and escalations
10. Provide support analytics

---

## 2. User Roles

### 2.1 Customer
- Start conversations
- Ask questions and get AI replies
- View message history
- Provide info the agent asks for
- Request a human agent
- View ticket status

### 2.2 Support Agent
- View escalated conversations and AI history
- Reply to customers and resolve tickets
- Update ticket status and take ownership
- View AI action summaries
- Add internal notes

### 2.3 Administrator
- Manage users and support agents
- Manage knowledge base documents
- Configure AI prompts, tools, APIs, escalation rules
- View conversations, tickets, escalations, analytics, audit logs

---

## 3. Functional Requirements

### 3.1 Authentication
- [ ] FR-AUTH-01: Email/password register and login
- [ ] FR-AUTH-02: JWT (or secure session) authentication
- [ ] FR-AUTH-03: Role-based access (customer / support_agent / admin)
- [ ] FR-AUTH-04: Optional Google OAuth (later)

### 3.2 Customer Chat
- [ ] FR-CHAT-01: Start a conversation (create conversation ID + status)
- [ ] FR-CHAT-02: Send message → store → send to AI agent → store reply
- [ ] FR-CHAT-03: Conversation statuses: `active`, `waiting_for_customer`, `escalated`, `resolved`, `closed`
- [ ] FR-CHAT-04: Show conversation history
- [ ] FR-CHAT-05: Support streaming AI responses

### 3.3 AI Agent (core)
- [ ] FR-AGENT-01: Detect customer intent
- [ ] FR-AGENT-02: Decide required action (answer / RAG / tool / ticket / escalate)
- [ ] FR-AGENT-03: Run an agent loop (reason → tool → observe → final answer)
- [ ] FR-AGENT-04: Estimate confidence and act by threshold
- [ ] FR-AGENT-05: Log every agent run (intent, confidence, tokens, latency)

**Intent categories**
- `general_question`
- `product_question`
- `billing_question`
- `subscription_question`
- `technical_support`
- `order_status`
- `refund_request`
- `account_issue`
- `complaint`
- `human_support_request`
- `unknown`

**Confidence rules**
- `> 0.80` → answer normally
- `0.60–0.80` → answer carefully
- `< 0.60` → consider escalation

### 3.4 Knowledge Base + RAG
- [ ] FR-KB-01: Admin uploads docs (FAQ, PDF, DOCX, text, policies, guides)
- [ ] FR-KB-02: Extract text → clean → chunk → embed → store
- [ ] FR-KB-03: Vector search (pgvector) on customer questions
- [ ] FR-KB-04: Send retrieved context to LLM before answering
- [ ] FR-KB-05: Cite sources (document, section, similarity score)
- [ ] FR-KB-06: Detect knowledge gaps when no good docs exist

### 3.5 Tool Calling
- [ ] FR-TOOL-01: AI may only call predefined backend tools (never raw DB)
- [ ] FR-TOOL-02: Log every tool call (name, input, output, status, time)

**MVP tools**
1. `search_knowledge_base`
2. `get_order_status`
3. `get_subscription`
4. `create_ticket`
5. `escalate_to_human`

**Later tools**
- `get_customer`
- `check_payment`
- `request_refund`
- `send_email`

**Tool permissions**
- Auto-allowed: search, order check, subscription check, create ticket
- Needs human approval: refund, cancel account, change subscription, issue credit

### 3.6 Tickets
- [ ] FR-TIX-01: Create tickets with: id, customer, conversation, title, description, priority, category, status, assignee, timestamps
- [ ] FR-TIX-02: Statuses: `open`, `in_progress`, `waiting_for_customer`, `resolved`, `closed`
- [ ] FR-TIX-03: Auto-create ticket when: low confidence, human requested, refund needed, security issue, payment dispute, complaint, tool failure

### 3.7 Escalation + Human Handoff
- [ ] FR-ESC-01: Escalation reasons: customer request, low confidence, billing dispute, refund, security, angry customer, failed answers, tool failure, unknown
- [ ] FR-ESC-02: Immediate escalate if customer asks for human
- [ ] FR-ESC-03: Escalate if confidence < 60%
- [ ] FR-ESC-04: Escalate if same question fails 3 times
- [ ] FR-ESC-05: On escalate: create/update ticket → status=`escalated` → notify support → human takes over → AI stops auto-replies

### 3.8 Memory
- [ ] FR-MEM-01: Short-term memory = recent messages (last 10–30)
- [ ] FR-MEM-02: Optional long-term customer prefs (name, language, plan) — no sensitive data auto-saved
- [ ] FR-MEM-03: Summarize long chats to reduce tokens

### 3.9 Dashboards
- [ ] FR-DASH-01: Support dashboard — conversations, tickets, escalations, AI summaries
- [ ] FR-DASH-02: Conversation detail — transcript + customer profile + intent + confidence + tools + escalation reason
- [ ] FR-DASH-03: Admin overview — totals, AI resolved, escalations, open tickets, response time, resolution rate, CSAT

### 3.10 Analytics + Feedback
- [ ] FR-AN-01: Conversation metrics (total, per day, length)
- [ ] FR-AN-02: AI metrics (resolution rate, escalation rate, failed answers, avg confidence)
- [ ] FR-AN-03: Knowledge metrics (top topics, missing knowledge, top docs)
- [ ] FR-AN-04: Support team metrics (resolved, response time, resolution time)
- [ ] FR-FB-01: Customer feedback (helpful / not helpful, optional 1–5 stars)

### 3.11 Prompt + Observability
- [ ] FR-PR-01: Admin can configure and version system prompts
- [ ] FR-OBS-01: Inspect flow: message → intent → knowledge → tool → result → final reply
- [ ] FR-OBS-02: Audit log important actions (login, upload, ticket, tool call, refund approval, prompt change)

---

## 4. API Requirements

### Auth
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET  /api/auth/me`

### Conversations
- `POST /api/conversations`
- `GET  /api/conversations`
- `GET  /api/conversations/{id}`
- `POST /api/conversations/{id}/messages`

### Tickets
- `POST  /api/tickets`
- `GET   /api/tickets`
- `GET   /api/tickets/{id}`
- `PATCH /api/tickets/{id}`

### Knowledge Base
- `POST   /api/knowledge/documents`
- `GET    /api/knowledge/documents`
- `DELETE /api/knowledge/documents/{id}`
- `POST   /api/knowledge/search`

### Agent
- `POST /api/agent/chat`
- `POST /api/agent/run`

### Analytics
- `GET /api/analytics/overview`
- `GET /api/analytics/conversations`
- `GET /api/analytics/agent-performance`

---

## 5. Database Tables

1. `users`
2. `customers`
3. `support_agents`
4. `conversations`
5. `messages`
6. `tickets`
7. `knowledge_documents`
8. `knowledge_chunks`
9. `embeddings`
10. `agent_runs`
11. `tool_calls`
12. `escalations`
13. `customer_feedback`
14. `audit_logs`
15. `notifications`

---

## 6. Non-Functional Requirements

### Security
- [ ] NFR-SEC-01: HTTPS
- [ ] NFR-SEC-02: Secure password hashing
- [ ] NFR-SEC-03: RBAC + API auth
- [ ] NFR-SEC-04: Input validation, rate limiting
- [ ] NFR-SEC-05: Protect against SQLi, XSS, CSRF
- [ ] NFR-SEC-06: Secure file uploads
- [ ] NFR-SEC-07: Prompt-injection defense
- [ ] NFR-SEC-08: Mask sensitive data (cards, passwords, tokens, PII) before LLM

### Performance
- [ ] NFR-PERF-01: Chat reply starts in 1–3 seconds
- [ ] NFR-PERF-02: RAG retrieval under 1 second
- [ ] NFR-PERF-03: Streaming responses supported

### Reliability
- [ ] NFR-REL-01: Graceful handling of LLM / DB / API / tool failures
- [ ] NFR-REL-02: Safe fallback to human support when needed

### Rate limits
- Chat: 30 requests/minute/customer  
- Auth: 5 failed attempts/minute  

---

## 7. Delivery Phases

### MVP
1. Auth (admin, support agent, customer)
2. Customer chat + history + streaming
3. RAG (upload → chunk → embed → search)
4. Agent (intent + RAG + tools + ticket/escalate decisions)
5. Tools: search, order status, subscription, create ticket, escalate
6. Dashboard: conversations, details, escalations, tickets, knowledge

### Phase 2
1. Feedback
2. Analytics
3. Prompt management
4. Human approval workflows
5. Email / Slack
6. Advanced memory
7. Knowledge gap detection
8. Agent performance analytics

### Phase 3
1. Voice / WhatsApp / Telegram / email channels
2. Multi-agent routing (billing, technical, order, account)
3. Multilingual
4. CRM integration
5. Sentiment + QA + supervisor agents

---

## 8. Acceptance Criteria

1. Customers can start AI conversations
2. AI remembers the current conversation
3. Admin can upload knowledge documents
4. Documents become embeddings
5. AI retrieves relevant knowledge with RAG
6. AI answers using retrieved docs
7. AI can call backend tools
8. AI can look up simulated order info
9. AI can create tickets
10. AI can escalate conversations
11. Support agents can view and take over escalations
12. Agent actions and tool calls are logged and visible
13. Conversation history persists
14. Roles and permissions are enforced

---

## 9. Build Order (for this repo)

| Step | Module | What to build |
|------|--------|----------------|
| 1 | `rag/` | Document store, chunking, embeddings, search |
| 2 | `tools/` | Order lookup, ticket create, escalate |
| 3 | `agents/` | Intent → RAG/tools → reply/escalate loop |
| 4 | Chat API | Wire chat to agent (not plain LLM only) |
| 5 | Dashboard | Show intent, tools used, escalations |
| 6 | Analytics | Resolution / escalation metrics |

---

## 10. Goal

This must not be a simple chatbot.  
It must be an **agentic** support system that can **reason, retrieve knowledge, call tools, keep memory, and hand off to humans**.
