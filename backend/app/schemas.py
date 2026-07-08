from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class HCPBase(BaseModel):
    name: str
    specialty: Optional[str] = None
    organization: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    history_notes: Optional[str] = None

class HCPCreate(HCPBase):
    pass

class HCPOut(HCPBase):
    id: int
    class Config:
        from_attributes = True

class MaterialOut(BaseModel):
    id: int
    name: str
    type: str
    product: str
    class Config:
        from_attributes = True

class SampleOut(BaseModel):
    id: int
    name: str
    product: str
    dosage: Optional[str] = None
    class Config:
        from_attributes = True

class FormFields(BaseModel):
    hcp_name: str = ""
    interaction_type: str = "Meeting"
    date: str = ""
    time: str = ""
    attendees: List[str] = []
    topics_discussed: str = ""
    materials_shared: List[str] = []
    samples_distributed: List[str] = []
    sentiment: str = "Neutral"  # Positive, Neutral, Negative
    outcomes: str = ""
    follow_up_actions: str = ""
    ai_suggested_follow_ups: List[str] = []

class InteractionCreate(BaseModel):
    hcp_name: str
    interaction_type: str
    date: str
    time: str
    attendees: List[str]
    topics_discussed: str
    materials_shared: List[str]
    samples_distributed: List[str]
    sentiment: str
    outcomes: str
    follow_up_actions: str
    ai_suggested_follow_ups: List[str]

class InteractionOut(BaseModel):
    id: int
    hcp_id: int
    date: Optional[str] = None
    time: Optional[str] = None
    interaction_type: Optional[str] = None
    attendees: Optional[List[str]] = None
    topics_discussed: Optional[str] = None
    sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    materials_shared: Optional[List[str]] = None
    samples_distributed: Optional[List[str]] = None
    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str
    current_form: FormFields

class ChatResponse(BaseModel):
    message: str
    form_data: FormFields
    suggested_follow_ups: List[str]
