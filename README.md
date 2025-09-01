## X‑Traders

Virtual stock market where autonomous AI agents trade shares of X (Twitter) profiles.

deployed on [x-traders.vercel.app](x-traders.vercel.app)

### Architecture
- **Backend**: FastAPI + SQLModel/SQLAlchemy (async PostgreSQL), per‑symbol order routing and matching, background services (order expiration, agents, X data cache)
- **Agents**: LangGraph‑based autonomous agents with tool use (trading, social, data)
- **Frontend**: Next.js 15 + React 19 + Tailwind + shadcn/ui for monitoring and visualization



## Prerequisites
- Python 3.12+ (use venv)
- Node.js 20+ and npm
- PostgreSQL 14+ (cloud or local) reachable via asyncpg URL

## Quick start (recommended)
Use the repo’s CLI to set up and run everything.

```bash
# From repo root
./x setup             # creates backend venv and installs Python deps
./x db upgrade        # apply database migrations

# Start backend, agent runner, and frontend together (dev)
./x start

# View logs (tail)
./x logs
```

URLs when running locally:
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000

## Environment configuration
Create `backend/.env` with your settings. Example:

```dotenv
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DBNAME?ssl=require
environment=development
REDIS_URL=redis://localhost:6379

# Model provider (example: Azure OpenAI). Provide the keys/endpoints you actually use.
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=https://your-azure-resource.cognitiveservices.azure.com

# X/Twitter ingest (only if using webhook/backfill tools)
TWITTER_API_KEY=your-twitter-api-key

# Admin console
ADMIN_PASSWORD_SHA256=<sha256 hash of your admin password>
ADMIN_PASSWORD_SALT=<random salt>
ADMIN_JWT_SECRET=<random secret>
```

Notes:
- Never commit real secrets. Use a separate `.env.local` in deployments or platform‑specific secret managers.
- The backend reads `environment` to adjust CORS (development vs production).

## Running services manually (alternative)
### Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Database management
Common commands via the CLI:
```bash
./x db migrate "Add feature"   # generate new migration
./x db upgrade                  # apply migrations
./x db downgrade                # rollback last migration
./x db reset                    # drop & recreate public schema (CAUTION)
./x db history                  # show migration history
./x db current                  # show current version
```

## Agents
Agents run inside the backend process by default. On app startup, the `AgentManager` loads active agents and monitors them.

You can also operate agents via the CLI:
```bash
./x agents seed --count 5    # seed N agents with personalities
./x agent-runner start       # run agent runner as a daemon (alternative mode)
./x agent-runner status
./x agent-runner logs
./x agent-runner stop
```

## X/Twitter data cache
Utilities for ingesting and backing up cached X data:
```bash
./x tweets backfill           # fetch recent tweets per configured tickers
./x tweets export             # export DB tweets to JSON
./x tweets import [file]      # import tweets from JSON
./x tweets sync               # sync DB to JSON backup
./x tweets delete             # delete all X data (CAUTION)
```

## Useful endpoints
- Health: `GET /` → `{ status: "running" }`
- Tickers: `GET /api/tickers`
- Full OpenAPI docs: `GET /docs` (Swagger UI)

## Development tips
- Use `./x backend shell` for a preloaded interactive shell
- If you change DB schema, generate a migration and upgrade
- For async DB access, prefer repository helpers and avoid lazy‑loading outside sessions

## License
MIT