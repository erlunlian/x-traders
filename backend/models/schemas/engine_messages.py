from enum import Enum
from uuid import UUID

from pydantic import BaseModel

from models.core import CancelReason


class MessageType(Enum):
    NEW_ORDER = "NEW_ORDER"
    CANCEL_ORDER = "CANCEL_ORDER"


class OrderMessage(BaseModel):
    """Base message for order queue"""

    order_id: UUID
    message_type: MessageType


class NewOrderMessage(OrderMessage):
    """Message to process a new order"""

    message_type: MessageType = MessageType.NEW_ORDER


class CancelOrderMessage(OrderMessage):
    """Message to cancel an order"""

    message_type: MessageType = MessageType.CANCEL_ORDER
    cancel_reason: CancelReason = CancelReason.USER
