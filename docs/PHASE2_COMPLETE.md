# AI Lead Response & Qualification System
## Phase 2: Integrations & Delivery - COMPLETE ✅

---

## 🎯 What Was Built in Phase 2

Production-ready integrations for **message delivery**, **knowledge retrieval (RAG)**, **calendar booking**, **CRM sync**, **email notifications**, and **background task processing**.

---

## 📁 New Files Created

```
app/
├── services/
│   └── knowledge_service.py      # RAG with pgvector (330 lines)
├── integrations/
│   ├── twilio_service.py         # SMS/WhatsApp delivery (380 lines)
│   ├── calendar_service.py       # Cal.com integration (320 lines)
│   ├── hubspot_service.py        # HubSpot CRM sync (480 lines)
│   └── email_service.py          # SendGrid/SMTP (520 lines)
├── api/routes/
│   └── knowledge.py              # Knowledge base API (280 lines)
└── worker.py                      # Celery background tasks (450 lines)
```

---

## 🔧 New Integration Components

### 1. Knowledge Base / RAG Service
`app/services/knowledge_service.py`

| Feature | Description |
|---------|-------------|
| Document Ingestion | Chunk documents with overlap, generate embeddings |
| FAQ Ingestion | Single or bulk FAQ import |
| Semantic Search | pgvector cosine similarity search |
| Client Isolation | Per-client namespace for knowledge |

**Chunking Strategy:**
- Chunk size: ~500 tokens
- Overlap: ~50 tokens
- Similarity threshold: 0.75

**Usage:**
```python
# Ingest FAQ
await kb_service.ingest_faq(kb_id, "What are your hours?", "Mon-Fri 9-5")

# Search
results = await kb_service.search(client_id, "business hours", max_results=3)
```

---

### 2. Twilio Service (SMS/WhatsApp/Voice)
`app/integrations/twilio_service.py`

| Method | Description |
|--------|-------------|
| `send_sms()` | Send SMS message |
| `send_whatsapp()` | Send WhatsApp message |
| `send_whatsapp_template()` | Send template (for cold outreach) |
| `make_call()` | Outbound call for hot lead alerts |
| `verify_signature()` | Webhook signature verification |
| `lookup_phone()` | Phone number lookup |

**Usage:**
```python
from app.integrations.twilio_service import get_twilio_service

twilio = get_twilio_service()
await twilio.send_sms(to="+966501234567", body="Thanks for your inquiry!")
await twilio.send_whatsapp(to="+966501234567", body="Welcome to our service")
```

---

### 3. Cal.com Calendar Service
`app/integrations/calendar_service.py`

| Method | Description |
|--------|-------------|
| `get_available_slots()` | Get available time slots |
| `get_next_available_slot()` | Get next open slot |
| `create_booking()` | Book appointment |
| `cancel_booking()` | Cancel existing booking |
| `reschedule_booking()` | Reschedule to new time |
| `format_slots_for_lead()` | Human-readable slot options |

**Usage:**
```python
from app.integrations.calendar_service import get_calendar_service

calendar = get_calendar_service(api_key="cal_live_xxx")
slots = await calendar.get_available_slots(event_type_id=123)
booking = await calendar.create_booking(
    event_type_id=123,
    start_time="2026-02-20T10:00:00Z",
    name="Ahmed",
    email="ahmed@example.com",
)
```

---

### 4. HubSpot CRM Service
`app/integrations/hubspot_service.py`

| Method | Description |
|--------|-------------|
| `create_contact()` | Create new contact |
| `update_contact()` | Update contact properties |
| `search_contact_by_email()` | Find by email |
| `search_contact_by_phone()` | Find by phone |
| `create_or_update_contact()` | Upsert contact |
| `create_deal()` | Create deal/opportunity |
| `update_deal_stage()` | Move deal through pipeline |
| `create_note()` | Log activity note |
| `log_conversation()` | Log AI conversation |
| `update_lead_score()` | Sync AI lead score |
| `sync_lead_data()` | Full lead sync |

**Custom Properties Created:**
- `ai_lead_score` - HOT/WARM/COLD
- `ai_service_interest` - Service they want
- `ai_urgency` - Urgency level
- `ai_budget_range` - Budget if provided
- `ai_timeline` - When they need service
- `ai_last_conversation` - Last AI interaction

**Usage:**
```python
from app.integrations.hubspot_service import get_hubspot_service

hubspot = get_hubspot_service()
await hubspot.sync_lead_data(
    email="lead@example.com",
    phone="+966501234567",
    name="Ahmed",
    lead_score="HOT",
    qualification_data={"service_interest": "home_inspection"},
    conversation_summary="Interested buyer with 800k budget",
)
```

---

### 5. Email Notification Service
`app/integrations/email_service.py`

| Method | Description |
|--------|-------------|
| `send_email()` | Generic email send |
| `send_hot_lead_alert()` | Hot lead notification to client |
| `send_escalation_alert()` | Human needed notification |
| `send_appointment_confirmation()` | Booking confirmation to lead |
| `send_daily_summary()` | Daily performance report |

**Providers:**
- SendGrid API (primary)
- SMTP fallback

**Email Templates Included:**
- 🔥 Hot Lead Alert (red theme)
- ⚠️ Escalation Alert (orange theme)
- ✓ Appointment Confirmation (green theme)
- 📊 Daily Summary Report (blue theme)

**Usage:**
```python
from app.integrations.email_service import get_email_service

email = get_email_service()
await email.send_hot_lead_alert(
    to="owner@realty.com",
    lead_name="Ahmed",
    lead_phone="+966501234567",
    service_interest="Buy apartment",
    urgency="This week",
)
```

---

### 6. Celery Background Worker
`app/worker.py`

| Task | Queue | Description |
|------|-------|-------------|
| `process_ai_response` | ai | Main AI processing flow |
| `generate_greeting` | ai | Initial greeting generation |
| `send_message_sms` | delivery | SMS delivery |
| `send_message_whatsapp` | delivery | WhatsApp delivery |
| `send_hot_lead_alert` | notifications | Hot lead email alert |
| `send_escalation_alert` | notifications | Escalation notification |
| `send_sms_alert` | notifications | Urgent SMS alert |
| `sync_lead_to_hubspot` | integrations | CRM sync |
| `sync_pending_crm_records` | integrations | Periodic CRM sync |
| `book_appointment` | integrations | Calendar booking |
| `send_daily_summaries` | reports | Daily report emails |
| `cleanup_old_data` | maintenance | Data retention cleanup |
| `update_token_usage` | maintenance | Token tracking |
| `ingest_document` | integrations | KB document ingestion |
| `bulk_ingest_faqs` | integrations | Bulk FAQ ingestion |

**Beat Schedule (Periodic Tasks):**
```python
"daily-summary": Every 24 hours
"cleanup-old-conversations": Every 24 hours
"sync-pending-crm": Every 5 minutes
```

**Run Worker:**
```bash
celery -A app.worker worker --loglevel=info
celery -A app.worker beat --loglevel=info  # Scheduler
```

---

## 📡 New API Endpoints

### Knowledge Base Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/knowledge/bases` | Create knowledge base |
| GET | `/api/v1/knowledge/bases/{kb_id}` | Get knowledge base |
| GET | `/api/v1/knowledge/client/{client_id}/bases` | List client's KBs |
| DELETE | `/api/v1/knowledge/bases/{kb_id}` | Delete knowledge base |
| POST | `/api/v1/knowledge/bases/{kb_id}/documents` | Ingest document |
| POST | `/api/v1/knowledge/bases/{kb_id}/faqs` | Ingest FAQ |
| POST | `/api/v1/knowledge/bases/{kb_id}/faqs/bulk` | Bulk ingest FAQs |
| POST | `/api/v1/knowledge/search` | Semantic search |
| GET | `/api/v1/knowledge/bases/{kb_id}/stats` | Get KB statistics |
| POST | `/api/v1/knowledge/bases/{kb_id}/clear` | Clear all chunks |

---

## 🔄 Updated Components

### Orchestrator Updates
`app/services/orchestrator.py`

**New Features:**
- ✅ RAG context injection into AI prompts
- ✅ Twilio SMS/WhatsApp message delivery
- ✅ Email notifications on escalation
- ✅ SMS alerts for hot leads
- ✅ HubSpot CRM sync on hot lead
- ✅ Cal.com appointment booking

### Config Updates
`app/core/config.py`

**New Settings:**
- Cal.com: `calcom_api_key`, `calcom_base_url`, `calcom_default_event_type_id`
- HubSpot: `hubspot_access_token`, `hubspot_portal_id`
- Email: `sendgrid_api_key`, `smtp_*`, `email_from_*`

---

## 🔧 Per-Client Configuration

Each client can have custom integration settings in their config JSON:

```json
{
  "twilio_phone_number": "+1234567890",
  "twilio_whatsapp_number": "whatsapp:+1234567890",
  "hot_lead_sms_number": "+1987654321",
  "calcom_api_key": "cal_live_xxx",
  "calcom_event_type_id": 123456,
  "hubspot_access_token": "pat-na1-xxx"
}
```

---

## 🚀 Using Phase 2 Features

### 1. Set Up Knowledge Base
```bash
# Create KB
curl -X POST "http://localhost:8000/api/v1/knowledge/bases?client_id={uuid}" \
  -H "Content-Type: application/json" \
  -d '{"name": "Company FAQs", "description": "Common questions"}'

# Add FAQs
curl -X POST "http://localhost:8000/api/v1/knowledge/bases/{kb_id}/faqs/bulk" \
  -d '{"faqs": [
    {"question": "What are your hours?", "answer": "Mon-Fri 9AM-6PM"},
    {"question": "Do you offer financing?", "answer": "Yes, we partner with..."}
  ]}'
```

### 2. Configure Integrations
```bash
# Update client with integration settings
curl -X PATCH "http://localhost:8000/api/v1/clients/{id}/config" \
  -d '{
    "twilio_phone_number": "+966...",
    "hot_lead_sms_number": "+966...",
    "calcom_api_key": "cal_live_...",
    "calcom_event_type_id": 123456
  }'
```

### 3. Start Workers
```bash
# In docker-compose, workers start automatically
docker-compose up

# Or manually:
celery -A app.worker worker -Q ai,delivery,notifications,integrations,reports,maintenance
celery -A app.worker beat
```

---

## ✅ Phase 2 Checklist

- [x] Knowledge Base Service (RAG)
  - [x] Document chunking
  - [x] Embedding generation (OpenAI)
  - [x] Semantic search (pgvector)
  - [x] FAQ ingestion
  - [x] API endpoints
- [x] Twilio Integration
  - [x] SMS sending
  - [x] WhatsApp sending
  - [x] Template messages
  - [x] Voice calls
  - [x] Webhook verification
- [x] Cal.com Integration
  - [x] Availability checking
  - [x] Appointment booking
  - [x] Cancellation/reschedule
  - [x] Auto-booking flow
- [x] HubSpot Integration
  - [x] Contact CRUD
  - [x] Deal management
  - [x] Activity logging
  - [x] Lead score sync
  - [x] Full lead sync
- [x] Email Notifications
  - [x] SendGrid integration
  - [x] SMTP fallback
  - [x] Hot lead alerts
  - [x] Escalation alerts
  - [x] Appointment confirmations
  - [x] Daily summaries
- [x] Celery Workers
  - [x] AI processing tasks
  - [x] Message delivery tasks
  - [x] Notification tasks
  - [x] CRM sync tasks
  - [x] Calendar tasks
  - [x] Report tasks
  - [x] Maintenance tasks
  - [x] Beat scheduler
- [x] Orchestrator Updates
  - [x] RAG context injection
  - [x] Twilio delivery
  - [x] Email notifications
  - [x] CRM sync
  - [x] Appointment booking

---

## 🔜 Coming in Phase 3

- Admin dashboard (React)
- Real-time analytics
- Conversation viewer
- Client onboarding wizard
- A/B testing for prompts
- Performance monitoring
- Production hardening
- Deployment scripts

---

## 📊 Integration Flow Diagram

```
Lead Message → Webhook → Create/Get Conversation
                              ↓
                    Load Client Config
                              ↓
                    ┌─────────────────┐
                    │ RAG Retrieval   │
                    │ (Knowledge Base)│
                    └────────┬────────┘
                              ↓
                    ┌─────────────────┐
                    │   AI Agent      │
                    │ (Claude Sonnet) │
                    └────────┬────────┘
                              ↓
            ┌─────────────────┼─────────────────┐
            ↓                 ↓                 ↓
     Hot Lead?         Book Appt?         Escalate?
         │                 │                  │
    ┌────┴────┐      ┌────┴────┐       ┌────┴────┐
    │ HubSpot │      │ Cal.com │       │  Email  │
    │  Sync   │      │ Booking │       │  Alert  │
    └────┬────┘      └────┬────┘       └────┬────┘
         │                │                  │
    ┌────┴────┐           │                  │
    │ SMS/Email│          │                  │
    │  Alert  │           │                  │
    └─────────┘           │                  │
                          ↓                  ↓
                    Send Response (Twilio SMS/WhatsApp)
```

---

## 🎉 Phase 2 Complete!

The system now has full integration capabilities.

**Request Phase 3** when ready for:
- Admin dashboard
- Analytics & reporting
- Production deployment
