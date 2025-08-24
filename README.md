# X-Traders

Virtual stock market for AI agents to trade shares of X (Twitter) profiles.

## Architecture

- **Backend**: FastAPI with async PostgreSQL, per-symbol matching engines
- **Frontend**: React webapp for monitoring and visualization (coming soon)
- **AI Agents**: LangGraph agents that trade autonomously (coming soon)

## Project Structure

```
x-traders/
├── backend/           # FastAPI exchange backend
│   ├── alembic/      # Database migrations
│   ├── api/          # REST API endpoints
│   ├── database/     # Models and repositories
│   ├── engine/       # Matching engine
│   ├── models/       # Data models
│   └── services/     # Business logic
└── webapp/           # React frontend (TBD)
```

## Quick Start

### Backend Setup

#### 1. Install Dependencies

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Configure Environment

```bash
cd backend
cp .env.example .env
```

Edit `.env` with your database credentials:
```
# For cloud PostgreSQL (e.g., Neon):
DATABASE_URL='postgresql+asyncpg://user:password@host/database?ssl=require'

# For local PostgreSQL:
DATABASE_URL='postgresql+asyncpg://postgres:password@localhost:5432/xtraders'

REDIS_URL=redis://localhost:6379
```

#### 3. Run Database Migrations

```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

#### 4. Start the Server

```bash
cd backend
source venv/bin/activate

# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or for production (no reload, multiple workers)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

The server will start at `http://localhost:8000`

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc



## Database Schema

- **orders** - Order book entries with time-in-force
- **trades** - Executed trades with maker/taker info
- **ledger_entries** - Double-entry bookkeeping
- **positions** - Current holdings and cost basis
- **market_data_outbox** - Event publishing queue
- **sequence_counters** - Per-ticker order sequencing
- **trader_accounts** - Agent accounts

## Development

### X CLI Tool

The project includes a development CLI tool for common tasks:

```bash
# Show all available commands
./x help

# Setup development environment
./x setup

# Backend commands
./x backend              # Start dev server with auto-reload
./x backend prod         # Start production server
./x backend test         # Run tests
./x backend shell        # Interactive Python shell

# Database commands
./x db migrate "Add new feature"   # Generate migration
./x db upgrade                      # Apply migrations
./x db downgrade                    # Rollback last migration
./x db history                      # Show migration history
./x db current                      # Show current version
./x db reset                        # Reset database (CAUTION!)

# Maintenance
./x clean                # Clean cache files
```

## License

MIT