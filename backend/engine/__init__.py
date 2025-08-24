"""
Engine package - provides the core exchange functionality
"""

from engine.order_expiration_service import OrderExpirationService
from engine.order_router import OrderRouter

# Singleton instances
order_router = OrderRouter()
expiration_service: OrderExpirationService = None

__all__ = [
    "order_router",
    "expiration_service",
    "OrderRouter",
    "OrderExpirationService",
]
