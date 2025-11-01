import requests
from app.config.settings import PUSHOVER_TOKEN, PUSHOVER_USER

def push(text: str):
    if PUSHOVER_TOKEN and PUSHOVER_USER:
        try:
            requests.post(
                "https://api.pushover.net/1/messages.json",
                data={"token": PUSHOVER_TOKEN, "user": PUSHOVER_USER, "message": text},
                timeout=5,
            )
        except Exception:
            pass

def record_unknown_question(question: str):
    push(f"Unknown question: {question}")
    return {"recorded": "ok"}

schema = {
    "name": "record_unknown_question",
    "description": "Record a question we couldn't answer.",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The unknown question"},
        },
        "required": ["question"],
        "additionalProperties": False
    }
}
