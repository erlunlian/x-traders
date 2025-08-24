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
    echo "  backend               Start the backend server (dev mode)"
    echo "  backend prod          Start the backend in production mode"
    echo "  backend test          Run backend tests"
    echo "  backend shell         Start Python shell with app context"
    echo ""
    echo "  db migrate [msg]      Generate a new database migration"
    echo "  db upgrade            Apply database migrations"
    echo "  db downgrade          Rollback last migration"
    echo "  db history            Show migration history"
    echo "  db current            Show current migration version"
    echo "  db reset              Drop and recreate all tables (CAUTION!)"
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
            echo -e "${RED}WARNING: This will drop all tables and data!${NC}"
            read -p "Are you sure? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo -e "${YELLOW}Resetting database...${NC}"
                cd "$BACKEND_DIR"
                activate_venv || exit 1
                
                # Drop all tables
                alembic downgrade base
                # Recreate all tables
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
    backend)
        backend_cmd "$2"
        ;;
    db)
        db_cmd "$2" "$3"
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