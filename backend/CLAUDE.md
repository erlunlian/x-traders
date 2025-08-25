# Project Guidelines for Claude

## Running the Application

**Always use the `./x` CLI to manage the application:**
Commands:
-  setup                 Set up the development environment

-  start                 Start both backend and frontend servers
-  stop                  Stop all running servers
-  status                Check server status
-  logs [backend|frontend] View server logs

-  backend               Start the backend server (dev mode)
-  backend prod          Start the backend in production mode
-  backend test          Run backend tests
-  backend shell         Start Python shell with app context

-  frontend              Start the frontend server (dev mode)
-  frontend build        Build frontend for production

-  db migrate [msg]      Generate a new database migration
-  db upgrade            Apply database migrations
-  db downgrade          Rollback last migration
-  db history            Show migration history
-  db current            Show current migration version
-  db reset              Drop and recreate all tables (CAUTION!)

-  clean                 Clean up cache files and __pycache__
-  help                  Show this help message


## Code Style Rules

### Type Safety
- **Never use dictionaries for structured data** - Always use Pydantic models, dataclasses, or typed classes
- Use proper type hints for all function parameters and return values
- Prefer enums over string literals for fixed sets of values

### Repository Pattern
- Repository methods that don't commit must be named with `_in_transaction` suffix
- Example: `create_order_in_transaction()`, `record_trade_in_transaction()`
- This makes it explicit that the caller must manage transaction boundaries

### Early Returns
- Avoid deep nesting in conditionals and loops
- Use early returns, continues, and breaks to reduce indentation
- Example:
  ```python
  # Bad
  if condition:
      if another_condition:
          do_something()
  
  # Good
  if not condition:
      return
  if not another_condition:
      return
  do_something()
  ```

### Naming Conventions
- Methods that may return None should be named `get_*_or_none()`
- Methods that raise if not found should be named `get_*()`
- All monetary values in cents should have `_in_cents` suffix in variable/parameter names

### Database Access
- All database queries must go through repository classes
- Never use SQLAlchemy sessions directly outside of repositories
- Keep transaction logic in services, not in repositories

### Error Handling
- Raise exceptions for programming errors (e.g., order not found when it should exist)
- Return None or use `_or_none` methods for expected cases (e.g., checking if something exists)