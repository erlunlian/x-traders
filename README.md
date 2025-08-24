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

### Using the X CLI (Recommended)

```bash
# Setup everything automatically
./x setup

# Configure your database
cd backend
cp .env.example .env
# Edit .env with your database credentials

# Apply database migrations
./x db upgrade

# Start the server
./x backend
```

The server will start at `http://localhost:8000`
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## Development

### X CLI Tool

The project includes a development CLI tool for common tasks:

```bash
# Show all available commands
./x help

# Setup development environment
./x setup

# Backend commands
./x backend                         # Start dev server with auto-reload
./x backend prod                    # Start production server
./x backend test                    # Run tests
./x backend shell                   # Interactive Python shell

# Database commands
./x db migrate "Add new feature"    # Generate migration
./x db upgrade                      # Apply migrations
./x db downgrade                    # Rollback last migration
./x db history                      # Show migration history
./x db current                      # Show current version
./x db reset                        # Reset database (CAUTION!)

# Maintenance
./x clean                           # Clean cache files
```

## License

MIT