import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import create_document, get_documents, db
from schemas import UserProfile, Report, ChatMessage, SymptomCheck, Reminder

# FastAPI app
app = FastAPI(title="AarogyaAI Backend", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helpers

def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB document to JSON-serializable dict."""
    if doc is None:
        return doc
    res = {}
    for k, v in doc.items():
        if k == "_id":
            res["id"] = str(v)
        elif isinstance(v, datetime):
            res[k] = v.isoformat()
        else:
            res[k] = v
    return res


@app.get("/")
def root():
    return {"app": "AarogyaAI Backend", "status": "ok"}


@app.get("/test")
def test_database():
    """Verify DB connectivity and list a few collections."""
    ok = db is not None
    cols: List[str] = []
    try:
        if ok:
            cols = db.list_collection_names()[:10]
    except Exception as e:  # pragma: no cover
        return {
            "backend": "running",
            "database": f"error: {str(e)[:80]}",
        }
    return {
        "backend": "running",
        "database": "connected" if ok else "not_configured",
        "collections": cols,
        "database_url": "set" if os.getenv("DATABASE_URL") else "unset",
        "database_name": "set" if os.getenv("DATABASE_NAME") else "unset",
    }


# Profile Endpoints
@app.post("/api/profile")
def create_profile(profile: UserProfile):
    # Ensure uniqueness by email (simple check)
    existing = get_documents("userprofile", {"email": profile.email}, limit=1)
    if existing:
        raise HTTPException(status_code=400, detail="Profile with this email already exists")
    new_id = create_document("userprofile", profile)
    return {"id": new_id}


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    theme: Optional[str] = None
    notifications_enabled: Optional[bool] = None


@app.put("/api/profile")
def update_profile(email: str, changes: ProfileUpdate):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    coll = db["userprofile"]
    found = coll.find_one({"email": email})
    if not found:
        raise HTTPException(status_code=404, detail="Profile not found")
    data = {k: v for k, v in changes.model_dump().items() if v is not None}
    data["updated_at"] = datetime.utcnow()
    coll.update_one({"email": email}, {"$set": data})
    return {"ok": True}


@app.get("/api/profile")
def get_profile(email: str):
    docs = get_documents("userprofile", {"email": email}, limit=1)
    if not docs:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _serialize(docs[0])


# Reports Endpoints
@app.post("/api/reports")
def create_report(report: Report):
    new_id = create_document("report", report)
    return {"id": new_id}


@app.get("/api/reports")
def list_reports(owner_email: Optional[str] = None, limit: int = Query(25, ge=1, le=100)):
    filt: Dict[str, Any] = {}
    if owner_email:
        filt["owner_email"] = owner_email
    docs = get_documents("report", filt, limit)
    return [_serialize(d) for d in docs]


# Chat Endpoints (placeholder AI)
@app.post("/api/chat")
def chat(message: ChatMessage):
    # Save user message
    user_msg_id = create_document("chatmessage", message)

    # Generate a simple placeholder response and save it
    reply_text = (
        "I'm your AarogyaAI assistant. While I can't provide medical diagnosis, "
        "I can help you track symptoms and suggest next steps. Could you share more details?"
    )
    assistant_msg = ChatMessage(
        conversation_id=message.conversation_id,
        role="assistant",
        content=reply_text,
        owner_email=message.owner_email,
    )
    assistant_msg_id = create_document("chatmessage", assistant_msg)

    return {"user_message_id": user_msg_id, "assistant_message_id": assistant_msg_id, "reply": reply_text}


@app.get("/api/chat/history")
def chat_history(conversation_id: Optional[str] = None, owner_email: Optional[str] = None, limit: int = Query(50, ge=1, le=200)):
    filt: Dict[str, Any] = {}
    if conversation_id:
        filt["conversation_id"] = conversation_id
    if owner_email:
        filt["owner_email"] = owner_email
    docs = get_documents("chatmessage", filt, limit)
    # Sort by created_at if present
    docs.sort(key=lambda d: d.get("created_at", datetime.utcnow()))
    return [_serialize(d) for d in docs]


# Symptom Checker
@app.post("/api/symptoms")
def submit_symptoms(entry: SymptomCheck):
    # Very simple heuristic placeholder for risk score
    count = len(entry.symptoms)
    sev_weight = {None: 0.2, "mild": 0.3, "moderate": 0.6, "severe": 0.85}[entry.severity]
    risk = min(1.0, 0.15 * count + sev_weight)
    assessment = (
        "Symptoms recorded. If symptoms worsen or you experience severe issues (e.g., chest pain, "
        "difficulty breathing), please seek immediate medical attention."
    )

    enriched = SymptomCheck(
        symptoms=entry.symptoms,
        duration=entry.duration,
        severity=entry.severity,
        notes=entry.notes,
        assessment=assessment,
        risk_score=risk,
        owner_email=entry.owner_email,
    )
    new_id = create_document("symptomcheck", enriched)
    return {"id": new_id, "risk_score": risk, "assessment": assessment}


@app.get("/api/symptoms")
def list_symptom_checks(owner_email: Optional[str] = None, limit: int = Query(25, ge=1, le=100)):
    filt: Dict[str, Any] = {}
    if owner_email:
        filt["owner_email"] = owner_email
    docs = get_documents("symptomcheck", filt, limit)
    return [_serialize(d) for d in docs]


# Reminders
@app.post("/api/reminders")
def create_reminder(reminder: Reminder):
    new_id = create_document("reminder", reminder)
    return {"id": new_id}


@app.get("/api/reminders")
def list_reminders(owner_email: Optional[str] = None, limit: int = Query(50, ge=1, le=100)):
    filt: Dict[str, Any] = {}
    if owner_email:
        filt["owner_email"] = owner_email
    docs = get_documents("reminder", filt, limit)
    return [_serialize(d) for d in docs]


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
