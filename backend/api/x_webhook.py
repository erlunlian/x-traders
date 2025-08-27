"""
API endpoint for receiving X/Twitter webhooks
"""

from database import get_db
from database.repositories import XDataRepository
from fastapi import APIRouter, Depends, Header, HTTPException, status
from models.schemas.webhook import WebhookPayload, WebhookProcessingResult
from services.x_webhook_service import XWebhookService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/webhook", tags=["x_webhook"])

# Initialize service
webhook_service = XWebhookService()


@router.post("/x/tweets", response_model=WebhookProcessingResult)
async def receive_tweet_webhook(
    payload: WebhookPayload,
    x_api_key: str = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> WebhookProcessingResult:
    """
    Receive tweet webhook from TwitterAPI.io

    This endpoint:
    1. Verifies the API key matches our configured key
    2. Validates that tweets are from usernames in our tickers list
    3. Stores valid tweets and user data in our cache
    4. Returns processing results
    """
    # Verify API key
    if not webhook_service.verify_api_key(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Process payload within transaction
    try:
        repo = XDataRepository(db)
        result = await webhook_service.process_webhook_without_commit(repo, payload)
        await db.commit()
        return result
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}",
        )
