# AI Lead Response & Qualification System
## Phase 1: Foundation - COMPLETE ✅

---

## 🎯 What Was Built

A **production-ready AI-powered lead qualification system** that automatically handles incoming leads across multiple channels, qualifies them using Claude AI, and routes hot leads for immediate follow-up.

---

## 📁 Project Structure

```
ai-lead-system/
├── app/
│   ├── main.py                    # FastAPI application entry
│   ├── agents/
│   │   ├── qualification_agent.py # Claude AI lead qualification
│   │   └── __init__.py
│   ├── api/
│   │   ├── webhooks.py            # Multi-channel webhooks
│   │   └── routes/
│   │       ├── health.py          # Health checks
│   │       ├── leads.py           # Lead CRUD API
│   │       ├── conversations.py   # Conversation API
│   │       └── clients.py         # Multi-tenant client API
│   ├── core/
│   │   └── config.py              # Type-safe configuration
│   ├── db/
│   │   ├── models.py              # SQLAlchemy models (638 lines)
│   │   └── session.py             # Async database sessions
│   ├── services/
│   │   ├── orchestrator.py        # Main conversation flow (524 lines)
│   │   ├── lead_service.py        # Lead business logic
│   │   ├── conversation_service.py # Conversation management
│   │   └── client_service.py      # Multi-tenant client management
│   └── integrations/              # Channel integrations (Phase 2)
├── docker-compose.yml             # Full dev environment
├── Dockerfile                     # Production-ready container
├── .env.example                   # Environment template
├── pyproject.toml                 # Dependencies
└── scripts/
    └── init-db.sql                # Database initialization
```

---

## 🔧 Core Components

### 1. Multi-Channel Lead Intake
| Channel | Webhook Endpoint | Status |
|---------|-----------------|--------|
| Web Form | `/webhooks/web-form` | ✅ Ready |
| SMS (Twilio) | `/webhooks/sms/inbound` | ✅ Ready |
| WhatsApp | `/webhooks/whatsapp/inbound` | ✅ Ready |
| Live Chat | `/webhooks/live-chat` | ✅ Ready |
| Missed Call | `/webhooks/missed-call` | ✅ Ready |

### 2. AI Qualification Engine
- **Primary Model**: Claude Sonnet 4 (qualification & response)
- **Fast Router**: Claude Haiku (quick routing decisions)
- **Lead Scoring**: HOT / WARM / COLD / UNSCORED
- **Extracted Data**:
  - Service interest
  - Budget range & confirmation
  - Urgency level
  - Timeline
  - Decision maker status
  - Location

### 3. Lead Lifecycle States
```
NEW → QUALIFYING → QUALIFIED → APPOINTMENT_BOOKED → HANDED_OFF
                 ↘ NURTURING
                 ↘ DISQUALIFIED
```

### 4. Automatic Escalation Triggers
- Lead requests human assistance
- Low AI confidence (<0.6)
- High-value lead detected
- Extended conversation (>20 exchanges)
- Keywords: "manager", "human", "agent", etc.

### 5. Multi-Tenant Architecture
- Per-client API keys (SHA-256 hashed)
- Per-client configuration
- Per-client token budgets
- Row-level security ready

---

## 🚀 Quick Start

### 1. Clone and Configure
```bash
cd ai-lead-system
cp .env.example .env
# Edit .env with your API keys
```

### 2. Required Environment Variables
```env
# Minimum required for Phase 1:
ANTHROPIC_API_KEY=sk-ant-your-key-here
SECRET_KEY=your-secret-key-min-32-chars-change-this
```

### 3. Start Development Environment
```bash
docker-compose up -d
```

This starts:
- **API Server**: http://localhost:8000
- **PostgreSQL**: localhost:5432 (with pgvector)
- **Redis**: localhost:6379

### 4. Verify Installation
```bash
curl http://localhost:8000/health
# {"status":"healthy","database":"connected"}
```

### 5. Create Your First Client
```bash
curl -X POST http://localhost:8000/api/v1/clients \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Realty",
    "slug": "test-realty",
    "industry": "real_estate",
    "timezone": "Asia/Riyadh",
    "business_hours": {
      "monday": {"start": "09:00", "end": "18:00"},
      "tuesday": {"start": "09:00", "end": "18:00"},
      "wednesday": {"start": "09:00", "end": "18:00"},
      "thursday": {"start": "09:00", "end": "18:00"},
      "friday": {"start": "09:00", "end": "13:00"}
    }
  }'
```

**Response includes your API key** - save it securely!

### 6. Test Lead Submission
```bash
curl -X POST http://localhost:8000/webhooks/web-form \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "name": "Ahmed",
    "phone": "+966501234567",
    "email": "ahmed@example.com",
    "message": "I am looking to buy an apartment in Dammam, budget around 800,000 SAR",
    "source": "website"
  }'
```

---

## 📡 API Endpoints

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check |
| GET | `/health/ready` | Readiness (with DB) |
| GET | `/health/live` | Liveness probe |

### Clients (Multi-Tenant)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/clients` | Create client |
| GET | `/api/v1/clients/{id}` | Get client |
| PATCH | `/api/v1/clients/{id}` | Update client |
| POST | `/api/v1/clients/{id}/activate` | Activate |
| POST | `/api/v1/clients/{id}/pause` | Pause |
| POST | `/api/v1/clients/{id}/rotate-api-key` | Rotate API key |
| GET | `/api/v1/clients/{id}/usage` | Token usage |

### Leads
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/leads` | Create lead |
| GET | `/api/v1/leads/{id}` | Get lead |
| PATCH | `/api/v1/leads/{id}` | Update lead |
| PATCH | `/api/v1/leads/{id}/score` | Update score |
| POST | `/api/v1/leads/{id}/handoff` | Human handoff |
| GET | `/api/v1/leads/client/{id}/hot` | Get hot leads |

### Conversations
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/conversations/{id}` | Get with messages |
| GET | `/api/v1/conversations/{id}/messages` | Get messages |
| POST | `/api/v1/conversations/{id}/messages` | Add message |
| POST | `/api/v1/conversations/{id}/escalate` | Escalate |
| GET | `/api/v1/conversations/client/{id}/active` | Active conversations |

### Webhooks (Lead Intake)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/webhooks/web-form` | Web form submission |
| POST | `/webhooks/sms/inbound` | Twilio SMS |
| POST | `/webhooks/whatsapp/inbound` | Twilio WhatsApp |
| POST | `/webhooks/live-chat` | Live chat widget |
| POST | `/webhooks/missed-call` | Missed call follow-up |

---

## 💡 Key Features

### AI Response Quality
- **Bilingual**: Arabic/English automatic detection
- **Context-Aware**: Remembers full conversation history
- **Brand Voice**: Matches client's tone and personality
- **Knowledge-Grounded**: Uses RAG (ready in Phase 2)

### Cost Controls
- Token usage tracking per client
- Monthly budget limits
- Usage alerts at 80% threshold
- Model routing (Haiku for simple, Sonnet for complex)

### Security
- API key authentication
- Twilio signature verification
- Secrets never in logs
- Non-root Docker containers

---

## 🔜 Coming in Phase 2

- RAG knowledge base retrieval
- Twilio SMS/WhatsApp delivery
- Calendar integration (Cal.com)
- CRM integrations (HubSpot)
- Email notifications
- Celery background tasks

---

## 🔜 Coming in Phase 3

- Admin dashboard
- Analytics & reporting
- A/B testing
- Production hardening
- Monitoring & alerting

---

## 📊 Technical Specifications

| Component | Technology |
|-----------|------------|
| Framework | FastAPI (async) |
| Database | PostgreSQL 16 + pgvector |
| ORM | SQLAlchemy 2.0 (async) |
| Cache | Redis 7 |
| AI | Anthropic Claude API |
| SMS/Voice | Twilio |
| Container | Docker + Docker Compose |
| Logging | structlog (JSON) |
| Errors | Sentry |

---

## 📝 Database Tables

| Table | Purpose |
|-------|---------|
| `clients` | Multi-tenant client accounts |
| `leads` | Lead records with qualification data |
| `conversations` | Conversation sessions |
| `messages` | Individual messages |
| `knowledge_base` | RAG document collections |
| `knowledge_chunks` | Vector embeddings |
| `qualification_rules` | Per-client rules |
| `escalations` | Escalation records |
| `usage_logs` | Token tracking |

---

## ✅ Phase 1 Checklist

- [x] Multi-tenant database schema
- [x] Async database sessions
- [x] FastAPI application
- [x] Health check endpoints
- [x] Multi-channel webhooks
- [x] Claude AI qualification agent
- [x] Claude Haiku router agent
- [x] Lead service (CRUD)
- [x] Conversation service
- [x] Client service
- [x] Orchestrator (main flow)
- [x] API authentication
- [x] Docker containerization
- [x] Development environment
- [x] Configuration management
- [x] Structured logging
- [x] Error tracking (Sentry)

---

## 🎉 Phase 1 Complete!

The foundation is built. You now have a working AI lead qualification system.

**Request Phase 2** to add:
- Live SMS/WhatsApp delivery
- RAG knowledge base
- Calendar booking
- CRM integrations
