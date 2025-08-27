"""
Engine package - provides the core exchange functionality
"""

from engine.order_expiration_service import OrderExpirationService
from engine.order_router import OrderRouter

# Singleton instance - only create the router
# The expiration service is created in main.py during startup
order_router = OrderRouter()

__all__ = [
    "order_router",
    "OrderExpirationService",
]
