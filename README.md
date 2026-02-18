# AI Lead Response & Qualification System

AI-powered lead qualification and response system built with FastAPI, Anthropic Claude, and modern async Python.

## Features

- Automated lead qualification using AI agents
- Multi-channel communication (Email, SMS, WhatsApp)
- Real-time conversation management
- CRM integration (HubSpot)
- Calendar scheduling
- Knowledge base management
- Role-based access control
- Rate limiting and security

## Quick Start

```bash
# Activate virtual environment
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Project Structure

```
app/
├── api/          # API routes and webhooks
├── agents/       # AI qualification agents
├── core/         # Configuration, auth, middleware
├── db/           # Database models and sessions
├── integrations/ # External service integrations
├── services/     # Business logic layer
└── utils/        # Utility functions
```

## Environment Variables

Copy `.env.example` to `.env` and configure the required variables.

## API Documentation

When running in development mode, API docs are available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
