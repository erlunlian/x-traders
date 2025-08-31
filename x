#!/bin/bash

# X-Traders Development CLI
# Usage: ./x <command> [subcommand] [options]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Check if we're in the right directory
if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}Error: backend directory not found${NC}"
    echo "Please run this script from the x-traders root directory"
    exit 1
fi

# Activate virtual environment if it exists
activate_venv() {
    if [ -f "$BACKEND_DIR/venv/bin/activate" ]; then
        source "$BACKEND_DIR/venv/bin/activate"
    else
        echo -e "${YELLOW}Warning: Virtual environment not found${NC}"
        echo "Run './x setup' to create it"
        return 1
    fi
}

# Print usage information
usage() {
    echo -e "${BLUE}X-Traders Development CLI${NC}"
    echo ""
    echo "Usage: ./x <command> [subcommand] [options]"
    echo ""
    echo "Commands:"
    echo "  setup                 Set up the development environment"
    echo ""
    echo "  start                 Start backend, frontend, and agent-runner"
    echo "  stop                  Stop all running servers"
    echo "  status                Check server status"
    echo "  logs [backend|frontend|agent] View server logs"
    echo ""
    echo "  backend               Start the backend server (dev mode)"
    echo "  backend prod          Start the backend in production mode"
    echo "  backend test          Run backend tests"
    echo "  backend shell         Start Python shell with app context"
    echo ""
    echo "  frontend              Start the frontend server (dev mode)"
    echo "  frontend build        Build frontend for production"
    echo ""
    echo "  agent-runner          Start the agent runner in foreground"
    echo "  agent-runner start    Start the agent runner (daemon)"
    echo "  agent-runner stop     Stop the agent runner"
    echo "  agent-runner status   Check agent runner status"
    echo "  agent-runner logs     Tail agent runner logs"
    echo ""
    echo "  db migrate [msg]      Generate a new database migration"
    echo "  db upgrade            Apply database migrations"
    echo "  db downgrade          Rollback last migration"
    echo "  db history            Show migration history"
    echo "  db current            Show current migration version"
    echo "  db reset              Drop and recreate all tables (CAUTION!)"
    echo ""
    echo "  treasury seed         Create/ensure treasury and list \$1 asks"
    echo "  agents seed [--count N]  Seed N AI agents with \$10k and personalities"
    echo ""
    echo "  tweets backfill       Fetch 100 tweets per ticker from API"
    echo "  tweets export         Export database tweets to JSON backup"
    echo "  tweets import [file]  Import tweets from JSON backup"
    echo "  tweets sync           Sync database to JSON backup"
    echo "  tweets delete         Delete all X data from database (CAUTION!)"
    echo ""
    echo "  clean                 Clean up cache files and __pycache__"
    echo "  help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./x setup"
    echo "  ./x backend"
    echo "  ./x backend test"
    echo "  ./x db migrate \"Add user preferences\""
    echo "  ./x db upgrade"
}

# Setup development environment
setup() {
    echo -e "${GREEN}Setting up development environment...${NC}"
    
    cd "$BACKEND_DIR"
    
    # Create virtual environment
    echo "Creating virtual environment..."
    python3 -m venv venv
    
    # Activate venv
    source venv/bin/activate
    
    # Install dependencies
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Copy .env.example if .env doesn't exist
    if [ ! -f .env ]; then
        echo "Creating .env file..."
        cp .env.example .env
        echo -e "${YELLOW}Please update .env with your database credentials${NC}"
    fi
    
    echo -e "${GREEN}Setup complete!${NC}"
    echo "Run './x db upgrade' to initialize the database"
}

# Backend commands
backend_cmd() {
    case "$1" in
        ""|dev)
            echo -e "${GREEN}Starting backend server (development mode)...${NC}"
            cd "$BACKEND_DIR"
            activate_venv || exit 1
            
            echo "Server starting at http://localhost:8000"
            echo "API docs at http://localhost:8000/docs"
            echo -e "${YELLOW}Auto-reload enabled${NC}"
            uvicorn main:app --reload --host 0.0.0.0 --port 8000
            ;;
        prod)
            echo -e "${GREEN}Starting backend server (production mode)...${NC}"
            cd "$BACKEND_DIR"
            activate_venv || exit 1
            
            echo "Starting with 4 workers..."
            uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
            ;;
        test)
            echo -e "${GREEN}Running backend tests...${NC}"
            cd "$BACKEND_DIR"
            activate_venv || exit 1
            
            if [ -d "tests" ]; then
                pytest tests/ -v
            else
                echo -e "${YELLOW}No tests directory found${NC}"
                echo "Create a 'tests' directory in backend/ to add tests"
            fi
            ;;
        shell)
            echo -e "${GREEN}Starting Python shell...${NC}"
            cd "$BACKEND_DIR"
            activate_venv || exit 1
            
            python -c "
import asyncio
from database import async_session, get_db_transaction
from database.models import *
from database.repositories import *
from models.core import *
from models.schemas import *
from models.responses import *
from services.trading import *
from engine import order_router

print('${GREEN}X-Traders Interactive Shell${NC}')
print('━' * 50)
print('Available imports:')
print('  • Database models (DBOrder, DBTrade, etc.)')
print('  • Repositories (OrderRepository, TradeRepository, etc.)')
print('  • Enums (OrderType, Side, Ticker, etc.)')
print('  • Trading functions (place_buy_order, place_sell_order, etc.)')
print('  • order_router - The main order routing engine')
print()
print('Example usage:')
print('  >>> trader_id = await create_trader()')
print('  >>> await place_buy_order(trader_id, \"@elonmusk\", 100)')
print('━' * 50)
"
            python
            ;;
        *)
            echo -e "${RED}Unknown backend subcommand: $1${NC}"
            echo "Available: backend, backend prod, backend test, backend shell"
            exit 1
            ;;
    esac
}

# Database commands
db_cmd() {
    case "$1" in
        migrate)
            local message="$2"
            if [ -z "$message" ]; then
                echo -e "${RED}Error: Migration message required${NC}"
                echo "Usage: ./x db migrate \"Your migration message\""
                exit 1
            fi
            
            echo -e "${GREEN}Generating migration: $message${NC}"
            cd "$BACKEND_DIR"
            activate_venv || exit 1
            
            alembic revision --autogenerate -m "$message"
            echo -e "${GREEN}Migration generated successfully${NC}"
            echo "Run './x db upgrade' to apply it"
            ;;
        upgrade)
            echo -e "${GREEN}Applying database migrations...${NC}"
            cd "$BACKEND_DIR"
            activate_venv || exit 1
            
            alembic upgrade head
            echo -e "${GREEN}Migrations applied successfully${NC}"
            ;;
        downgrade)
            echo -e "${YELLOW}Rolling back last migration...${NC}"
            cd "$BACKEND_DIR"
            activate_venv || exit 1
            
            alembic downgrade -1
            echo -e "${GREEN}Rollback complete${NC}"
            ;;
        history)
            echo -e "${BLUE}Migration history:${NC}"
            cd "$BACKEND_DIR"
            activate_venv || exit 1
            
            alembic history
            ;;
        current)
            echo -e "${BLUE}Current migration version:${NC}"
            cd "$BACKEND_DIR"
            activate_venv || exit 1
            
            alembic current
            ;;
        reset)
            echo -e "${RED}WARNING: This will drop ALL objects in the 'public' schema (tables, enums, etc.) and erase ALL data!${NC}"
            read -p "Are you sure? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo -e "${YELLOW}Resetting database (drop schema, then re-run migrations)...${NC}"
                cd "$BACKEND_DIR"
                activate_venv || exit 1

                # Use Python + SQLAlchemy to drop and recreate the public schema to remove tables, enums, sequences, etc.
                python - <<'PY'
import os
import asyncio
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Explicitly load .env from the current working directory (backend)
dotenv_path = Path.cwd() / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path=str(dotenv_path))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL is not set in environment or .env")

async def drop_and_recreate_public_schema() -> None:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"statement_cache_size": 0},
    )
    async with engine.begin() as conn:
        # Drop the public schema (drops all contained objects) and recreate it
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        # Optional: grant usage to all; adjust as needed for your DB user
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        # Ensure search_path is set properly
        await conn.execute(text("SET search_path TO public"))
    await engine.dispose()

asyncio.run(drop_and_recreate_public_schema())
print("Schema 'public' dropped and recreated.")
PY

                # Recreate all tables by applying migrations from base to head
                alembic upgrade head
                echo -e "${GREEN}Database reset complete${NC}"
            else
                echo "Cancelled"
            fi
            ;;
        *)
            echo -e "${RED}Unknown db subcommand: $1${NC}"
            echo "Available: migrate, upgrade, downgrade, history, current, reset"
            exit 1
            ;;
    esac
}

# Tweet backup commands
tweets_cmd() {
    case "$1" in
        backfill)
            echo -e "${GREEN}Starting tweet backfill...${NC}"
            cd "$BACKEND_DIR"
            activate_venv || exit 1
            
            # Pass additional arguments (like --force)
            shift
            if [ $# -gt 0 ]; then
                python scripts/backfill/backfill_tweets.py "$@"
            else
                python scripts/backfill/backfill_tweets.py
            fi
            ;;
        export)
            echo -e "${GREEN}Exporting tweets to JSON backup...${NC}"
            cd "$BACKEND_DIR"
            activate_venv || exit 1
            
            python scripts/backfill/export_tweets.py
            ;;
        import)
            echo -e "${GREEN}Importing tweets from JSON backup...${NC}"
            cd "$BACKEND_DIR"
            activate_venv || exit 1
            
            # Pass the file argument if provided
            shift
            python scripts/backfill/import_tweets.py "$@"
            ;;
        sync)
            echo -e "${GREEN}Syncing database to JSON backup...${NC}"
            cd "$BACKEND_DIR"
            activate_venv || exit 1
            
            python scripts/backfill/sync_tweets.py
            ;;
        delete)
            echo -e "${YELLOW}WARNING: This will delete all X/Twitter data from the database!${NC}"
            read -p "Are you sure? (y/N): " confirm
            if [[ $confirm == [yY] ]]; then
                echo -e "${GREEN}Deleting X/Twitter data...${NC}"
                cd "$BACKEND_DIR"
                activate_venv || exit 1
                python scripts/delete_x_data.py
            else
                echo -e "${BLUE}Cancelled${NC}"
            fi
            ;;
        *)
            echo -e "${RED}Unknown tweets subcommand: $1${NC}"
            echo "Available: backfill, export, import, sync, delete"
            echo ""
            echo "Examples:"
            echo "  ./x tweets backfill          # Fetch tweets from API"
            echo "  ./x tweets backfill --force   # Force refresh all data"
            echo "  ./x tweets export             # Export DB to JSON"
            echo "  ./x tweets import             # Import from latest backup"
            echo "  ./x tweets import --list      # List available backups"
            echo "  ./x tweets sync               # Sync DB to backup"
            echo "  ./x tweets delete             # Delete all X data from DB (CAUTION!)"
            exit 1
            ;;
    esac
}

# Agents commands
agents_cmd() {
    case "$1" in
        seed)
            echo -e "${GREEN}Seeding AI agents...${NC}"
            cd "$BACKEND_DIR"
            activate_venv || exit 1
            shift
            # Forward optional --count argument(s)
            if [ $# -gt 0 ]; then
                python -m scripts.seed_agents "$@"
            else
                python -m scripts.seed_agents
            fi
            ;;
        *)
            echo -e "${RED}Unknown agents subcommand: $1${NC}"
            echo "Available: seed"
            exit 1
            ;;
    esac
}

# Agent runner controls
agent_runner_cmd() {
    case "$1" in
        ""|run|foreground)
            echo -e "${GREEN}Starting agent runner (foreground)...${NC}"
            cd "$BACKEND_DIR"
            activate_venv || exit 1
            python -m services.agents.runner
            ;;
        start)
            if pgrep -f "python -m services.agents.runner" > /dev/null; then
                echo -e "${YELLOW}Agent runner is already running${NC}"
                exit 0
            fi
            echo -e "${GREEN}Starting agent runner (daemon)...${NC}"
            cd "$BACKEND_DIR"
            activate_venv || exit 1
            nohup python -m services.agents.runner > "$BACKEND_DIR/agent_runner.log" 2>&1 &
            echo $! > "$BACKEND_DIR/agent_runner.pid"
            echo -e "${GREEN}Agent runner started (PID: $(cat $BACKEND_DIR/agent_runner.pid))${NC}"
            ;;
        stop)
            if [ -f "$BACKEND_DIR/agent_runner.pid" ]; then
                PID=$(cat "$BACKEND_DIR/agent_runner.pid")
                if kill -0 $PID 2>/dev/null; then
                    kill $PID
                    echo -e "${GREEN}Agent runner stopped${NC}"
                fi
                rm "$BACKEND_DIR/agent_runner.pid"
            else
                pkill -f "python -m services.agents.runner" 2>/dev/null && echo -e "${GREEN}Agent runner stopped${NC}" || echo -e "${YELLOW}Agent runner not running${NC}"
            fi
            ;;
        status)
            if pgrep -f "python -m services.agents.runner" > /dev/null; then
                echo -e "Agent Runner: ${GREEN}● Running${NC}"
            else
                echo -e "Agent Runner: ${RED}● Stopped${NC}"
            fi
            ;;
        logs)
            if [ -f "$BACKEND_DIR/agent_runner.log" ]; then
                echo -e "${BLUE}Agent Runner Logs:${NC}"
                tail -f "$BACKEND_DIR/agent_runner.log"
            else
                echo -e "${YELLOW}No agent runner logs found${NC}"
            fi
            ;;
        *)
            echo -e "${RED}Unknown agent-runner subcommand: $1${NC}"
            echo "Available: agent-runner [run|start|stop|status|logs]"
            exit 1
            ;;
    esac
}

# Treasury commands
treasury_cmd() {
    case "$1" in
        seed)
            echo -e "${GREEN}Seeding treasury account and orders...${NC}"
            cd "$BACKEND_DIR"
            activate_venv || exit 1
            python -m scripts.seed_treasury
            ;;
        *)
            echo -e "${RED}Unknown treasury subcommand: $1${NC}"
            echo "Available: seed"
            exit 1
            ;;
    esac
}

# Start both servers
start() {
    echo -e "${GREEN}Starting X-Traders servers...${NC}"
    
    # Check if servers are already running
    if pgrep -f "uvicorn main:app" > /dev/null; then
        echo -e "${YELLOW}Backend server is already running${NC}"
    else
        echo "Starting backend server..."
        cd "$BACKEND_DIR"
        activate_venv || exit 1
        nohup uvicorn main:app --reload --host 0.0.0.0 --port 8000 > "$BACKEND_DIR/server.log" 2>&1 &
        echo $! > "$BACKEND_DIR/server.pid"
        echo -e "${GREEN}Backend started (PID: $(cat $BACKEND_DIR/server.pid))${NC}"
    fi
    
    # Start agent runner
    if pgrep -f "python -m services.agents.runner" > /dev/null; then
        echo -e "${YELLOW}Agent runner is already running${NC}"
    else
        echo "Starting agent runner..."
        cd "$BACKEND_DIR"
        activate_venv || exit 1
        nohup python -m services.agents.runner > "$BACKEND_DIR/agent_runner.log" 2>&1 &
        echo $! > "$BACKEND_DIR/agent_runner.pid"
        echo -e "${GREEN}Agent runner started (PID: $(cat $BACKEND_DIR/agent_runner.pid))${NC}"
    fi

    if [ -d "$FRONTEND_DIR" ]; then
        if pgrep -f "next dev" > /dev/null; then
            echo -e "${YELLOW}Frontend server is already running${NC}"
        else
            echo "Starting frontend server..."
            cd "$FRONTEND_DIR"
            nohup npm run dev > "$FRONTEND_DIR/server.log" 2>&1 &
            echo $! > "$FRONTEND_DIR/server.pid"
            echo -e "${GREEN}Frontend started (PID: $(cat $FRONTEND_DIR/server.pid))${NC}"
        fi
    fi
    
    echo ""
    echo -e "${GREEN}Servers are running:${NC}"
    echo "  Backend:  http://localhost:8000"
    echo "  API Docs: http://localhost:8000/docs"
    echo "  Frontend: http://localhost:3000"
    echo "  Agent Runner: running (separate process)"
    echo ""
    echo "Run './x logs' to view server logs"
    echo "Run './x stop' to stop all servers"
}

# Stop all servers
stop() {
    echo -e "${YELLOW}Stopping servers...${NC}"
    
    # Stop backend
    if [ -f "$BACKEND_DIR/server.pid" ]; then
        PID=$(cat "$BACKEND_DIR/server.pid")
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            echo -e "${GREEN}Backend server stopped${NC}"
        fi
        rm "$BACKEND_DIR/server.pid"
    else
        # Try to find and kill by process name
        pkill -f "uvicorn main:app" 2>/dev/null && echo -e "${GREEN}Backend server stopped${NC}"
    fi
    
    # Stop agent runner
    if [ -f "$BACKEND_DIR/agent_runner.pid" ]; then
        PID=$(cat "$BACKEND_DIR/agent_runner.pid")
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            echo -e "${GREEN}Agent runner stopped${NC}"
        fi
        rm "$BACKEND_DIR/agent_runner.pid"
    else
        pkill -f "python -m services.agents.runner" 2>/dev/null && echo -e "${GREEN}Agent runner stopped${NC}"
    fi

    # Stop frontend
    if [ -f "$FRONTEND_DIR/server.pid" ]; then
        PID=$(cat "$FRONTEND_DIR/server.pid")
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            echo -e "${GREEN}Frontend server stopped${NC}"
        fi
        rm "$FRONTEND_DIR/server.pid"
    else
        # Try to find and kill by process name
        pkill -f "next dev" 2>/dev/null && echo -e "${GREEN}Frontend server stopped${NC}"
    fi
    
    echo -e "${GREEN}All servers stopped${NC}"
}

# Check server status
status() {
    echo -e "${BLUE}Server Status:${NC}"
    echo ""
    
    # Check backend
    if pgrep -f "uvicorn main:app" > /dev/null; then
        echo -e "Backend:  ${GREEN}● Running${NC} (http://localhost:8000)"
    else
        echo -e "Backend:  ${RED}● Stopped${NC}"
    fi
    
    # Check frontend
    if pgrep -f "next dev" > /dev/null; then
        echo -e "Frontend: ${GREEN}● Running${NC} (http://localhost:3000)"
    else
        echo -e "Frontend: ${RED}● Stopped${NC}"
    fi

    # Check agent runner
    if pgrep -f "python -m services.agents.runner" > /dev/null; then
        echo -e "Agent:    ${GREEN}● Running${NC}"
    else
        echo -e "Agent:    ${RED}● Stopped${NC}"
    fi
}

# View server logs
logs() {
    case "$1" in
        backend)
            if [ -f "$BACKEND_DIR/server.log" ]; then
                echo -e "${BLUE}Backend Server Logs:${NC}"
                tail -f "$BACKEND_DIR/server.log"
            else
                echo -e "${YELLOW}No backend logs found${NC}"
            fi
            ;;
        frontend)
            if [ -f "$FRONTEND_DIR/server.log" ]; then
                echo -e "${BLUE}Frontend Server Logs:${NC}"
                tail -f "$FRONTEND_DIR/server.log"
            else
                echo -e "${YELLOW}No frontend logs found${NC}"
            fi
            ;;
        "")
            # Show both logs
            echo -e "${BLUE}Server Logs (Press Ctrl+C to exit):${NC}"
            echo ""
            if [ -f "$BACKEND_DIR/server.log" ] && [ -f "$FRONTEND_DIR/server.log" ] && [ -f "$BACKEND_DIR/agent_runner.log" ]; then
                tail -f "$BACKEND_DIR/server.log" "$FRONTEND_DIR/server.log" "$BACKEND_DIR/agent_runner.log"
            elif [ -f "$BACKEND_DIR/server.log" ]; then
                tail -f "$BACKEND_DIR/server.log"
            elif [ -f "$FRONTEND_DIR/server.log" ]; then
                tail -f "$FRONTEND_DIR/server.log"
            elif [ -f "$BACKEND_DIR/agent_runner.log" ]; then
                tail -f "$BACKEND_DIR/agent_runner.log"
            else
                echo -e "${YELLOW}No server logs found${NC}"
            fi
            ;;
        agent)
            if [ -f "$BACKEND_DIR/agent_runner.log" ]; then
                echo -e "${BLUE}Agent Runner Logs:${NC}"
                tail -f "$BACKEND_DIR/agent_runner.log"
            else
                echo -e "${YELLOW}No agent runner logs found${NC}"
            fi
            ;;
        *)
            echo -e "${RED}Unknown log type: $1${NC}"
            echo "Usage: ./x logs [backend|frontend|agent]"
            exit 1
            ;;
    esac
}

# Frontend commands
frontend_cmd() {
    if [ ! -d "$FRONTEND_DIR" ]; then
        echo -e "${RED}Frontend directory not found${NC}"
        echo "The frontend application has not been set up yet"
        exit 1
    fi
    
    case "$1" in
        ""|dev)
            echo -e "${GREEN}Starting frontend server (development mode)...${NC}"
            cd "$FRONTEND_DIR"
            
            echo "Server starting at http://localhost:3000"
            echo -e "${YELLOW}Auto-reload enabled${NC}"
            npm run dev
            ;;
        build)
            echo -e "${GREEN}Building frontend for production...${NC}"
            cd "$FRONTEND_DIR"
            npm run build
            echo -e "${GREEN}Build complete!${NC}"
            ;;
        *)
            echo -e "${RED}Unknown frontend subcommand: $1${NC}"
            echo "Available: frontend, frontend build"
            exit 1
            ;;
    esac
}

# Clean up cache files
clean() {
    echo -e "${GREEN}Cleaning up cache files...${NC}"
    
    # Remove Python cache
    find "$SCRIPT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$SCRIPT_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
    find "$SCRIPT_DIR" -type f -name "*.pyo" -delete 2>/dev/null || true
    find "$SCRIPT_DIR" -type f -name ".DS_Store" -delete 2>/dev/null || true
    
    # Remove pytest cache
    find "$SCRIPT_DIR" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    
    # Remove mypy cache
    find "$SCRIPT_DIR" -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
    
    echo -e "${GREEN}Cleanup complete${NC}"
}

# Main command handler
case "$1" in
    setup)
        setup
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    status)
        status
        ;;
    logs)
        logs "$2"
        ;;
    backend)
        backend_cmd "$2"
        ;;
    frontend)
        frontend_cmd "$2"
        ;;
    agent-runner)
        agent_runner_cmd "$2"
        ;;
    db)
        db_cmd "$2" "$3"
        ;;
    tweets)
        tweets_cmd "${@:2}"
        ;;
    agents)
        agents_cmd "${@:2}"
        ;;
    treasury)
        treasury_cmd "$2"
        ;;
    clean)
        clean
        ;;
    help|--help|-h)
        usage
        ;;
    "")
        usage
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        usage
        exit 1
        ;;
esac