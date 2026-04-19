# 1KeyCore

1KeyCore is a production-grade multi-tenant LLM gateway built from scratch. Companies (tenants) register their own LLM API keys, their employees get access via JWT auth, and the gateway handles everything in between — routing, rate limiting, caching, and usage tracking — all isolated per tenant.

Built as a learning project to deeply understand how LLM infrastructure works at scale. Inspired by tools like Portkey and Helicone, but built ground up to understand every layer.

---

## Why 1KeyCore?

The naive approach to giving employees LLM access is handing out API keys directly. That creates real problems:

- **Security** — keys get leaked, committed to git, shared on Slack, left by employees who quit
- **No control** — one employee can burn unlimited budget with no way to stop them
- **No visibility** — no idea who used what model, how many tokens, what it cost
- **No flexibility** — switching models means updating every client application

1KeyCore solves all of this in one backend layer. Tenants register their key once. Employees just send requests. The gateway handles everything else.

---

## How It Works

```
![alt text](image.png)
```

---

## Features

### Multi-tenancy

Every tenant is completely isolated. Data, keys, rate limits, and cache entries never bleed across organizations. Enforced at the query level on every database operation — tenant_id is a required filter on all sensitive queries.

Each tenant has exactly one admin (the first user to register). Only the admin can register API keys, update rate limits, and manage the organization.

### BYOK — Bring Your Own Key

Tenants register their own API keys from OpenAI, Anthropic, Gemini, Groq, Mistral, or Cohere. Keys are stored using AES-256 Fernet symmetric encryption. The raw key is never returned after registration — not in responses, not in logs, nowhere. 1KeyCore never pays for a single LLM call.

### JWT Authentication

Users authenticate with email and password. On login they receive a JWT containing their `user_id`, `tenant_id`, and `email`. This token is validated on every protected request — the gateway knows exactly which user from which tenant is making each call without an additional database lookup.

### Multi-Layer Rate Limiting

Rate limiting runs across three independent dimensions before any request reaches the LLM:

**RPM (Requests Per Minute)** uses the token bucket algorithm. Tokens refill at `limit/60` per second continuously, eliminating the burst problem of fixed window counters. A user hitting their limit gets gradual access back rather than waiting for a hard 60-second reset.

**TPM (Tokens Per Minute)** uses a fixed window counter. Each request deducts an estimated token count pre-call, with actual token counts reconciled from the provider response post-call. Fixed window is appropriate here since token estimation is inherently approximate.

**Concurrency** uses a simple Redis atomic counter — incremented at request start, decremented in a `finally` block so it always releases even if the LLM call fails. This prevents a single user from bypassing RPM limits by firing many simultaneous requests.

All three limits are enforced independently per user AND per tenant:

```
Tenant A's users hitting their limit → Tenant B unaffected
User A hitting their limit → User B in same tenant unaffected
```

Redis keys follow a versioned namespace pattern:
```
v1:rl:rpm:{tenant_id}:{user_id}     ← user RPM token bucket
v1:rl:rpm:{tenant_id}               ← tenant RPM token bucket
v1:rl:tpm:{tenant_id}:{user_id}     ← user TPM counter
v1:rl:tpm:{tenant_id}               ← tenant TPM counter
v1:rl:conc:{tenant_id}:{user_id}    ← user concurrency counter
v1:rl:conc:{tenant_id}              ← tenant concurrency counter
```

The `v1:` prefix enables schema migration without breaking existing rate limit state.

### Two-Layer Caching

Caching only applies to deterministic requests (`temperature=None or temperature=0`). Non-deterministic requests always hit the LLM.

**Exact Cache** stores responses in Redis keyed by a SHA-256 hash of the canonical request (tenant, model, message, max_tokens, temperature, system_prompt hash). Identical requests return instantly from Redis with zero database or LLM involvement.

**Semantic Cache** stores request embeddings in PostgreSQL using pgvector. Incoming messages are embedded using `sentence-transformers` (`all-MiniLM-L6-v2`, 384 dimensions), then compared against stored embeddings using cosine distance. If a sufficiently similar query exists (distance < 0.15, equivalent to similarity > 0.85) the cached response is returned — no LLM call needed.

Cache is scoped per tenant. "What is the refund policy?" from Tenant A never returns a cached response from Tenant B's query "how do I get a refund?"

### Model Routing

A single `/chat` endpoint accepts any supported model name. The gateway resolves the correct provider, fetches the tenant's encrypted key for that provider, translates the request to the provider's specific API format, and returns a normalized response. Switching models requires zero changes on the client side.

### Smart Routing (Opt-in)

When `smart_routing: true` is set, the gateway scores the complexity of the incoming request using a heuristic (message length, keyword signals, system prompt presence) to classify it as economy, standard, or premium. It then selects the cheapest available model that matches the tier from providers the tenant has registered keys for.

Users always see which model actually handled their request alongside which model they requested.

### System Prompt Support

Requests can include an optional `system_prompt`. The system prompt hash is included in cache keys to ensure different system prompts never return each other's cached responses. Each provider receives the system prompt in its native format — OpenAI and Groq as a system message, Anthropic as a top-level `system` field.

---

## Supported Providers

| Provider | Models |
|---|---|
| OpenAI | gpt-4o, gpt-4o-mini, gpt-3.5-turbo |
| Anthropic | claude-3-5-sonnet-20241022, claude-3-haiku-20240307 |
| Gemini | gemini-1.5-pro, gemini-1.5-flash |
| Groq | llama-3.3-70b-versatile, llama3-8b-8192 |
| Mistral | mistral-large-latest, mistral-small-latest |
| Cohere | command-r-plus, command-r |

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| API | FastAPI (async) | Native async support, automatic OpenAPI docs |
| Database | PostgreSQL + pgvector | Relational data + vector similarity search in one DB |
| Cache / Rate limiting | Redis (Upstash) | In-memory speed, atomic operations, TTL support |
| ORM | SQLAlchemy (async) | Type-safe queries, async session management |
| Auth | JWT via python-jose | Stateless, carries tenant context without DB lookup |
| Encryption | Fernet (AES-256) | Symmetric encryption for API key storage |
| Embeddings | sentence-transformers | Free, local, no API cost for semantic cache |
| HTTP client | httpx | Async HTTP for LLM provider calls |
| Deployment | DigitalOcean + Neon + Upstash | Managed Postgres and Redis, zero ops overhead |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Tenant (Acme Corp)                 │
│                                                     │
│  Admin registers keys    Users send requests        │
│  POST /keys              POST /chat { msg, model }  │
└────────────┬─────────────────────┬──────────────────┘
             │                     │ JWT
             ▼                     ▼
┌─────────────────────────────────────────────────────┐
│                   1KeyCore Gateway                  │
│                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ Rate Limiter│  │ Exact Cache  │  │Semantic    │  │
│  │ RPM+TPM+    │  │ SHA-256 hash │  │Cache       │  │
│  │ Concurrency │  │ Redis TTL    │  │pgvector    │  │
│  │ Redis       │  └──────────────┘  │cosine sim  │  │
│  └─────────────┘                    └────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │              Model Router                    |   │
│  │  Resolves provider → decrypts key → routes   │   │
│  │  Smart routing: complexity score → tier      │   │
│  └──────────────────────┬───────────────────────┘   │
└─────────────────────────┼───────────────────────────┘
                          ▼
         ┌────────────────────────────────┐
         │  OpenAI  Anthropic  Gemini     │
         │  Groq    Mistral    Cohere     │
         └────────────────────────────────┘
```

---

## API Reference

### Auth

```
POST /tenant/              Create a new tenant (returns tenant_id)
POST /auth/register        Register a user with tenant_id
POST /auth/login           Login → returns JWT
```

### Keys (admin only)

```
POST   /keys/              Register an LLM provider API key
```

### Chat

```
POST /chat/                Send a message, receive a response
```

**Request:**
```json
{
  "message": "explain the CAP theorem",
  "model": "llama-3.3-70b-versatile",
  "system_prompt": "You are a concise technical assistant",
  "temperature": null,
  "max_tokens": 512,
  "smart_routing": false
}
```

**Response:**
```json
{
  "response": "The CAP theorem states...",
  "model": "llama-3.3-70b-versatile",
  "requested_model": "llama-3.3-70b-versatile",
  "cached": false,
  "tokens_used": 187,
  "estimated_cost": 0.0000094
}
```

---

## Integration

Any application can use 1KeyCore by replacing direct LLM provider calls with a single gateway call:

```python
# Before — calling OpenAI directly
import openai
response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "hello"}]
)

# After — calling 1KeyCore
import httpx
response = httpx.post(
    "https://api.1keycore.com/chat/",
    headers={"Authorization": "Bearer <employee_jwt>"},
    json={"model": "gpt-4o", "message": "hello"}
)
```

One URL change. All rate limiting, caching, and routing handled automatically.

---

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL with pgvector extension (Neon recommended)
- Redis (Upstash recommended)

### Installation

```bash
git clone https://github.com/saurabhje/1keycore
cd 1keycore
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

```bash
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname?ssl=require
SECRET_KEY=your-jwt-secret-key
ENCRYPTION_KEY=your-fernet-key
REDIS_URL=rediss://default:password@endpoint.upstash.io:6379
REDIS_TOKEN=your-upstash-token
ENV=development
```

Generate keys:
```bash
# JWT secret
python -c "import secrets; print(secrets.token_hex(32))"

# Fernet encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Enable pgvector in your PostgreSQL database:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Run

```bash
uvicorn main:app --reload
```

API docs at `http://localhost:8000/docs`

---

## Project Structure

```
1keycore/
├── main.py                    # App entry, router registration
├── requirements.txt
├── .env
└── app/
    ├── models.py             
    ├── schemas.py             
    ├── database.py            
    ├── security.py           
    ├── dependencies.py        
    ├── config.py              
    ├── redis.py               
    ├── routers/
    │   ├── tenant.py          
    │   ├── auth.py            
    │   ├── keys.py            
    │   └── chat.py            
        ├── constants.py       
        ├── providers.py       
        ├── rate_limiter.py   
        ├── redis_keys.py      
        ├── cache.py          
        ├── semantic_cache.py  
        └── router.py
```

---

## Design Decisions

**Why token bucket for RPM and fixed window for TPM?**
Token bucket eliminates the burst problem at window boundaries — tokens refill continuously so users can't double their rate limit by timing requests around the reset. TPM stays fixed window because token estimation is inherently approximate (using tiktoken pre-call, reconciling with actual counts post-call), so the additional accuracy of token bucket doesn't add real value.

**Why pgvector over a dedicated vector database?**
Semantic cache entries are always scoped to a tenant and filtered by model and system prompt — they're relational queries with a vector component, not pure vector search. PostgreSQL + pgvector handles this naturally without adding another service to operate.

**Why BYOK instead of a shared key?**
A shared key means you pay for every LLM call. BYOK means tenants pay their own providers directly. It also means you can't accidentally leak one tenant's usage to another's bill, and tenants maintain full control over their API key lifecycle.

**Why hardcode providers and models?**
For v1, hardcoding is a conscious tradeoff — simpler to build, easy to explain, no migration complexity. The production approach is a DB-driven provider registry where adding a new model is a row insert, not a code change. Noted as a v2 improvement.

---

## Roadmap

- [x] Usage tracking endpoint — tokens, cost, cache savings per tenant
- [x] Per-tenant spend limits and monthly budgets
- [ ] Model tier restrictions per tenant (free/pro/enterprise)
- [ ] DB-driven provider and model registry (replace hardcoded dicts)
- [x] Docker Compose for local development
- [x] Azure deployment with health checks
- [ ] Webhook support for rate limit and spend alerts
- [ ] SDK — Python and JavaScript wrappers around the REST API
- [ ] Embedding-based complexity classifier to replace heuristic smart router
- [ ] Streaming response support

---

## Author

Saurabh Singh — [linkedin.com/in/saurabhje](https://linkedin.com/in/saurabhje) · [github.com/saurabhje](https://github.com/saurabhje)

Built in public. Follow along on LinkedIn and X (@saurabhje) for updates as each layer ships.
