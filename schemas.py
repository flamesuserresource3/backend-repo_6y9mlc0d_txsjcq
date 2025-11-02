"""
AarogyaAI Database Schemas

Each Pydantic model represents one MongoDB collection.
Collection name is the lowercase class name (e.g., UserProfile -> "userprofile").
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

# Core user profile for settings and personalization
class UserProfile(BaseModel):
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Primary email (unique)")
    phone: Optional[str] = Field(None, description="Phone number")
    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[Literal["male", "female", "other", "prefer_not_to_say"]] = None
    height_cm: Optional[float] = Field(None, ge=0)
    weight_kg: Optional[float] = Field(None, ge=0)
    theme: Literal["dark", "light", "system"] = Field("dark", description="UI theme preference")
    notifications_enabled: bool = Field(True)

# Health report metadata (files are typically stored in cloud; we save metadata + links)
class Report(BaseModel):
    title: str
    report_type: Literal[
        "blood_test",
        "scan",
        "prescription",
        "discharge_summary",
        "other",
    ] = "other"
    report_date: Optional[datetime] = None
    file_url: Optional[str] = Field(None, description="Public or signed URL to the file")
    notes: Optional[str] = None
    owner_email: EmailStr

# Chat turns for AI assistant conversations
class ChatMessage(BaseModel):
    conversation_id: Optional[str] = Field(None, description="Client-generated conversation/thread id")
    role: Literal["user", "assistant"]
    content: str
    owner_email: Optional[EmailStr] = None

# Symptom checker submissions and results
class SymptomCheck(BaseModel):
    symptoms: List[str]
    duration: Optional[str] = Field(None, description="e.g., '3 days'")
    severity: Optional[Literal["mild", "moderate", "severe"]] = None
    notes: Optional[str] = None
    assessment: Optional[str] = Field(None, description="AI/heuristic assessment text")
    risk_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    owner_email: Optional[EmailStr] = None

# Simple reminder entries for meds/activities
class Reminder(BaseModel):
    title: str
    schedule: str = Field(..., description="Human-readable schedule, e.g., 'Daily 8:00 AM'")
    active: bool = True
    owner_email: Optional[EmailStr] = None
