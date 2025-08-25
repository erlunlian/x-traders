import asyncio
from contextlib import asynccontextmanager
from typing import List

import uvicorn
from api.admin import router as admin_router
from api.exchange import router as exchange_router
from api.market_data import router as market_data_router
from api.portfolio import router as portfolio_router
from api.traders import router as traders_router
from api.x_webhook import router as x_webhook_router
from config import TICKERS
from database import init_db
from dotenv import load_dotenv
from engine import OrderExpirationService, order_router
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle - startup and shutdown.
    """
    # Startup
    print("Starting X-Traders Exchange...")

    # Initialize database
    await init_db()

    # Initialize order router and processors
    await order_router.initialize(TICKERS)

    # Start order expiration service
    expiration_service = OrderExpirationService(order_router)
    expiration_task = asyncio.create_task(expiration_service.start())

    print(f"Exchange ready with {len(TICKERS)} tickers")

    yield

    # Shutdown
    print("Shutting down X-Traders Exchange...")

    # Stop services
    await expiration_service.stop()

    # Shutdown order router
    await order_router.shutdown()

    # Cancel background tasks
    expiration_task.cancel()

    print("Exchange shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="X-Traders Exchange",
    description="Virtual stock market for AI agents to trade X (Twitter) profiles",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(exchange_router, prefix="/api/exchange", tags=["Exchange"])
app.include_router(portfolio_router, prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(market_data_router, prefix="/api/market-data", tags=["Market Data"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(traders_router, prefix="/api/traders", tags=["Traders"])
app.include_router(x_webhook_router, prefix="/api", tags=["Webhooks"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "running", "exchange": "X-Traders"}


@app.get("/api/tickers")
async def get_tickers() -> List[str]:
    """Get list of tradeable tickers"""
    from engine import order_router

    if not order_router:
        raise HTTPException(status_code=503, detail="Exchange not initialized")
    return order_router.get_tickers()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
