from fastapi import APIRouter
from pydantic import BaseModel
import random

router = APIRouter(prefix="/api")

class Answer(BaseModel):
    session_id: int
    username: str
    question_id: int
    selected_option: int
    time_taken: float

mock_questions = [
    {
        "id": 1,
        "text": "What is the derivative of x^2?",
        "options": ["x", "2x", "x^2", "2"],
        "difficulty": "Easy",
        "domain": "Calculus",
        "correct": 1
    },
    {
        "id": 2,
        "text": "Solve for x: 2x + 5 = 15",
        "options": ["5", "10", "2", "7.5"],
        "difficulty": "Easy",
        "domain": "Algebra",
        "correct": 0
    },
    {
        "id": 3,
        "text": "What is the eigenvalue of identity matrix?",
        "options": ["0", "1", "-1", "Depends"],
        "difficulty": "Medium",
        "domain": "Linear Algebra",
        "correct": 1
    }
]

@router.get("/next_question/{session_id}")
def next_question(session_id: int):
    # Mock logic: random question
    # In reality, this would check session state
    if random.random() > 0.8: # 20% chance to finish
         return {"complete": True}
    
    q = random.choice(mock_questions)
    return {
        "complete": False,
        "question": {
            "id": q["id"],
            "text": q["text"],
            "options": q["options"],
            "difficulty": q["difficulty"],
            "domain": q["domain"]
        }
    }

@router.post("/submit_answer")
def submit_answer(answer: Answer):
    # Mock check: always correct or random
    is_correct = random.choice([True, False])
    return {"correct": is_correct}
