"""
IntelliPrep Main Website — FastAPI Application Entry Point
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routers import auth, dashboard, test, analytics
from app.db import init_pool
from app.templates_env import templates

app = FastAPI(title="IntelliPrep", docs_url=None, redoc_url=None)

# ── Static files & templates ───────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ── Startup ────────────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    init_pool()

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(test.router)
app.include_router(analytics.router)

# ── Root redirect ──────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return RedirectResponse("/dashboard", status_code=302)

# ── 404 handler ────────────────────────────────────────────────────────────────
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return templates.TemplateResponse(
        request, "errors/404.html", status_code=404
    )
