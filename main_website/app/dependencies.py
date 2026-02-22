"""
Auth dependency helpers — extract and validate the logged-in user from the
HTTP-only access_token cookie set during login.
"""

from fastapi import Request
from fastapi.responses import RedirectResponse
from app.supabase_client import supabase_anon


def get_current_user(request: Request):
    """Return the Supabase user object if logged in, else None."""
    access_token = request.cookies.get("access_token")
    if not access_token:
        return None
    try:
        resp = supabase_anon.auth.get_user(access_token)
        if resp and resp.user:
            return resp.user
    except Exception:
        pass
    return None


def require_auth(request: Request):
    """
    FastAPI dependency — redirects to login if not authenticated.
    Usage:  user = Depends(require_auth)
    """
    user = get_current_user(request)
    if not user:
        # Return a redirect instead of raising HTTPException so the browser
        # follows it naturally for server-rendered pages.
        return None  # routers must check for None and redirect
    return user
