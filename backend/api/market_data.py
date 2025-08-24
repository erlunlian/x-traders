"""
Market data API endpoints (placeholder for now - WebSocket support to be added later)
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def market_status():
    """
    Get market status.
    """
    return {"status": "open", "message": "Market is operational"}
