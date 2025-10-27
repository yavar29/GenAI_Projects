import os, requests
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

def record_user_details(email: str, name: str = "Name not provided", notes: str = "not provided"):
    push(f"Recording {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}

schema = {
    "name": "record_user_details",
    "description": "Record a user's contact details and context notes.",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {"type": "string", "description": "User's email"},
            "name": {"type": "string", "description": "User's name, if provided"},
            "notes": {"type": "string", "description": "Context from the conversation"}
        },
        "required": ["email"],
        "additionalProperties": False
    }
}
