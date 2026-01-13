from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/test")
templates = Jinja2Templates(directory="app/templates")

@router.get("/start", response_class=HTMLResponse)
def start_test(request: Request):
    return templates.TemplateResponse(
        "test/start.html",
        {"request": request}
    )
