from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db import init_pool, close_all
from app.routers import auth, pages, test_pages, test_api

app = FastAPI()

@app.on_event("startup")
def startup_event():
    init_pool()

@app.on_event("shutdown")
def shutdown_event():
    close_all()

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(pages.router)
app.include_router(test_pages.router)
app.include_router(test_api.router)
