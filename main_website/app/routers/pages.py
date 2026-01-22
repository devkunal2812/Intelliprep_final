from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "home.html",
        {"request": request}
    )

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    # Mock data for dashboard
    mock_user = {"username": "GuestUser"}
    mock_stats = {
        "overall_accuracy": 0.75,
        "attempts_count": 12,
        "avg_time": 45.5,
        "accuracy_by_domain": {
            "Calculus": 0.8,
            "Algebra": 0.6,
            "Geometry": 0.9
        },
        "accuracy_by_difficulty": {
            "Easy": 0.95,
            "Medium": 0.70,
            "Hard": 0.50
        }
    }
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": mock_user,
            "stats": mock_stats
        }
    )
