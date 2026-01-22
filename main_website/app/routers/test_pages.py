from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import random

router = APIRouter(prefix="/test")
templates = Jinja2Templates(directory="app/templates")

@router.get("/start", response_class=HTMLResponse)
def start_test_page(request: Request):
    return templates.TemplateResponse(
        "test/start.html",
        {"request": request}
    )

@router.post("/start")
def start_test_action():
    # Create a mock session ID
    session_id = random.randint(1000, 9999)
    return RedirectResponse(f"/test/question/{session_id}", status_code=302)

@router.get("/question/{session_id}", response_class=HTMLResponse)
def question_page(request: Request, session_id: int):
    return templates.TemplateResponse(
        "test/question.html",
        {
            "request": request,
            "session_id": session_id
        }
    )

@router.get("/complete/{session_id}", response_class=HTMLResponse)
def complete_page(request: Request, session_id: int):
    # Mock summary data
    mock_summary = {
        "username": "GuestUser",
        "attempted_count": 10,
        "attempted": [101, 102, 103, 104, 105], # Mock question IDs
        "accuracy": 0.8
    }
    return templates.TemplateResponse(
        "test/complete.html",
        {
            "request": request,
            "session_id": session_id,
            "summary": mock_summary
        }
    )
