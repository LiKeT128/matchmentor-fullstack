"""API routers package."""

from app.api.auth import router as auth_router
from app.api.matches import router as matches_router
from app.api.coaches import router as coaches_router
from app.api.payments import router as payments_router
from app.api.bookings import router as bookings_router
from app.api.sessions import router as sessions_router
from app.api.compat import router as compat_router
from app.api.demo import router as demo_router
from app.api.debug import router as debug_router

__all__ = [
    "auth_router",
    "matches_router", 
    "coaches_router",
    "payments_router",
    "bookings_router",
    "sessions_router",
    "compat_router",
    "demo_router",
    "debug_router",
]
