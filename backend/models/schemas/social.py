from uuid import UUID

from pydantic import BaseModel, Field


class CreatePostInput(BaseModel):
    ticker: str = Field(description="Ticker symbol, e.g. '@elonmusk'")
    content: str = Field(description="Post content")


class AddCommentInput(BaseModel):
    post_id: UUID
    content: str


class LikePostInput(BaseModel):
    post_id: UUID
