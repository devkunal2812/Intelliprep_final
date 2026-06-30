"""
Authentication router — login, register, logout.
Uses Supabase Auth (email + password only).
Sets / clears an HTTP-only access_token cookie.
"""

from fastapi import APIRouter, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies import get_current_user
from app.supabase_client import supabase_anon
from app.templates_env import templates

router = APIRouter(prefix="/auth", tags=["auth"])


# ──────────────────────────────────────────────────────────────────────────────
# Login
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if get_current_user(request):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "auth/login.html")


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    try:
        resp = supabase_anon.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        response = RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="access_token",
            value=resp.session.access_token,
            httponly=True,
            max_age=60 * 60 * 24 * 7,
            samesite="lax",
        )
        return response
    except Exception as e:
        err = str(e)
        if "Invalid login credentials" in err:
            err = "Invalid email or password."
        return templates.TemplateResponse(
            request, "auth/login.html", {"error": err}, status_code=401
        )


# ──────────────────────────────────────────────────────────────────────────────
# Register
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    if get_current_user(request):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "auth/register.html")


@router.post("/register")
def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    if password != confirm_password:
        return templates.TemplateResponse(
            request, "auth/register.html",
            {"error": "Passwords do not match."}, status_code=400
        )
    if len(password) < 6:
        return templates.TemplateResponse(
            request, "auth/register.html",
            {"error": "Password must be at least 6 characters."}, status_code=400
        )

    try:
        resp = supabase_anon.auth.sign_up({"email": email, "password": password})

        if resp.session:
            response = RedirectResponse(
                "/dashboard", status_code=status.HTTP_303_SEE_OTHER
            )
            response.set_cookie(
                key="access_token",
                value=resp.session.access_token,
                httponly=True,
                max_age=60 * 60 * 24 * 7,
                samesite="lax",
            )
            return response
        else:
            return templates.TemplateResponse(
                request, "auth/login.html",
                {"success": "Registration successful! Please check your email to confirm your account, then log in."},
            )

    except Exception as e:
        err = str(e)
        if "already registered" in err.lower() or "already exists" in err.lower():
            err = "This email is already registered. Please log in."
        return templates.TemplateResponse(
            request, "auth/register.html", {"error": err}, status_code=400
        )


# ──────────────────────────────────────────────────────────────────────────────
# Logout
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/logout")
def logout():
    response = RedirectResponse("/auth/login", status_code=302)
    response.delete_cookie("access_token")
    return response
