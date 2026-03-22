# Gatewise

> Multi-tenant LLM gateway — bring your own keys, control your usage.

Gatewise is a backend infrastructure layer that sits between your application and LLM providers. Companies (tenants) register their own API keys, their users send requests, and Gatewise handles routing, rate limiting, caching, and usage tracking — all isolated per tenant.

Built as a learning project to understand how LLM infrastructure works at scale. Inspired by tools like Portkey and Helicone.

---

## Why Gatewise?

If a company wants to give their employees access to LLMs, the naive approach is handing out API keys directly. That creates problems:

- **No control** — any employee can spend unlimited budget
- **No visibility** — no idea who used what, how much it cost
- **Security risk** — API keys get leaked, committed to git, shared on Slack
- **No flexibility** — switching models requires updating every client

Gatewise solves all of this in one backend layer.

---

## How It Works
```
Tenant admin registers their OpenAI / Anthropic / Gemini / Groq / Mistral / Cohere key
                        ↓
              Key stored AES-encrypted in PostgreSQL
                        ↓
         Tenant shares their tenant_id with employees
                        ↓
              Employees sign up and get a JWT
                        ↓
           Employee sends POST /chat { message, model }
                        ↓
    Gateway validates JWT → extracts tenant_id → checks rate limit
                        ↓
         Checks semantic cache → similar query answered before?
                        ↓
      Fetches tenant's encrypted key → decrypts → routes to provider
                        ↓
            Logs usage (tokens, cost, latency) per tenant
                        ↓
                  Returns response
```

---

## Features

### Multi-tenancy
Every tenant is completely isolated. Data, keys, rate limits, and usage logs never bleed across organizations. Enforced at the database level on every query.

### BYOK — Bring Your Own Key
Tenants register their own LLM provider keys. Keys are stored AES-encrypted using Fernet symmetric encryption. The raw key is never returned after registration. Gatewise never pays for LLM calls — the tenant's key is always used.

### Model Routing
Users specify a model name (`gpt-4o`, `claude-sonnet`, `llama-3.3-70b`). Gatewise resolves the correct provider, fetches the tenant's key for that provider, and routes the request. Switching models requires zero code changes on the client side.

### Rate Limiting
Per-tenant rate limiting using Redis sliding window counters. Tenants can be configured with different limits — free tier, pro tier, enterprise. Returns `429 Too Many Requests` with a `Retry-After` header when exceeded.

### Semantic Caching
Incoming prompts are embedded and compared against cached responses using pgvector cosine similarity. If a similar enough query has been answered before, the cached response is returned — no LLM call made. Cache is scoped per tenant so responses never leak across organizations.

### Usage Tracking
Every request is logged: tenant, user, model, provider, tokens in, tokens out, estimated cost, latency, cache hit or miss. Tenant admins can query their usage and cost breakdown via the API.

---

## Supported Providers

| Provider | Models |
|---|---|
| OpenAI | gpt-4o, gpt-4o-mini, gpt-3.5-turbo |
| Anthropic | claude-3-5-sonnet-20241022, claude-3-haiku-20240307 |
| Gemini | gemini-1.5-pro, gemini-1.5-flash |
| Groq | llama-3.3-70b-versatile, mixtral-8x7b-32768 |
| Mistral | mistral-large-latest, mistral-small-latest |
| Cohere | command-r-plus, command-r |

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI (async) |
| Database | PostgreSQL + pgvector |
| Cache / Rate limiting | Redis |
| ORM | SQLAlchemy (async) |
| Auth | JWT via python-jose |
| Encryption | Fernet (AES) via cryptography |
| HTTP client | httpx |
| Deployment | Docker Compose + DigitalOcean |

---

## Architecture
```
┌─────────────────────────────────────────┐
│           Tenant (Acme Corp)            │
│  Admin registers keys  │  Users chat    │
└────────────┬───────────────────┬────────┘
             │ POST /keys        │ POST /chat
             ▼                   ▼
┌─────────────────────────────────────────┐
│              Gatewise Gateway           │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐  │
│  │   Rate   │ │ Semantic │ │  Usage  │  │
│  │ Limiter  │ │  Cache   │ │ Tracker │  │
│  │  Redis   │ │ pgvector │ │Postgres │  │
│  └──────────┘ └──────────┘ └─────────┘  │
│         ┌───────────────────┐           │
│         │   Model Router    │           │
│         │  Decrypts key     │           │
│         │  Routes provider  │           │
│         └─────────┬─────────┘           │
└───────────────────┼─────────────────────┘
                    ▼
     ┌──────────────────────────┐
     │  OpenAI  Anthropic  Groq │
     │  Gemini  Mistral  Cohere │
     └──────────────────────────┘
```

---

## API Reference

### Auth
```
POST /tenant               Create a new tenant
POST /auth/register        Register a user under a tenant
POST /auth/login           Login and receive JWT
```

### Keys (admin only)
```
POST /keys                 Register an LLM provider API key
```

### Chat
```
POST /chat                 Send a message, get a response
```

### Usage (coming soon)
```
GET /usage                 Tenant usage and cost breakdown
GET /usage/cache           Cache hit rate and savings
```

---

## Getting Started

### Prerequisites
- Python 3.12+
- PostgreSQL (or Neon)
- Redis

### Installation
```bash
git clone https://github.com/saurabhje/gatewise
cd gatewise
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file:
```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost/gatewise
SECRET_KEY=your-secret-key
ENCRYPTION_KEY=your-fernet-key
ENV=development
```

Generate an encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Run
```bash
uvicorn main:app --reload
```

API docs available at `http://localhost:8000/docs`

---

## Project Structure
```
gatewise/
├── main.py
├── requirements.txt
├── .env
└── app/
    ├── models.py          # SQLAlchemy models
    ├── schemas.py         # Pydantic schemas
    ├── database.py        # Async engine and session
    ├── security.py        # JWT, bcrypt, Fernet encryption
    ├── dependencies.py    # get_current_user, get_admin_user
    ├── config.py          # Settings from .env
    └── routers/
        ├── tenant.py      # Tenant creation
        ├── auth.py        # Register and login
        ├── keys.py        # API key management
        └── chat.py        # LLM gateway endpoint
```

---

## Roadmap

- [ ] Redis rate limiting
- [ ] Semantic cache with pgvector
- [ ] Usage tracking and cost dashboard
- [ ] Simple demo UI
- [ ] Docker Compose setup
- [ ] DigitalOcean deployment
- [ ] DB-driven provider and model registry (replace hardcoded dicts)
- [ ] Per-user rate limits within a tenant
- [ ] Webhook support for usage alerts

---

## What I Learned

Building Gatewise taught me how multi-tenant SaaS backends work in practice — tenant isolation, encrypted credential storage, per-tenant rate limiting, and semantic similarity search. Every design decision has a reason behind it that I can explain.

---

## Author

Saurabh Singh — [linkedin.com/in/saurabhje](https://linkedin.com/in/saurabhje) · [github.com/saurabhje](https://github.com/saurabhje)