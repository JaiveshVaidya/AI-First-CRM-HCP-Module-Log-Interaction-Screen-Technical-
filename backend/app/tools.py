import json
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from .database import SessionLocal
from .models import HCP, Material, Sample, SuggestedFollowUp

# Helper function to open db session
def get_db_session():
    return SessionLocal()

@tool
def log_interaction(
    hcp_name: str,
    date: Optional[str] = None,
    time: Optional[str] = None,
    interaction_type: Optional[str] = "Meeting",
    sentiment: Optional[str] = "Neutral",
    topics_discussed: Optional[str] = None,
    outcomes: Optional[str] = None,
    follow_up_actions: Optional[str] = None,
    attendees: Optional[List[str]] = None
) -> str:
    """
    Extracts and logs the structured fields from an interaction.
    Arguments:
    - hcp_name: The name of the healthcare professional (e.g., Dr. Smith, Dr. John).
    - date: Date of the interaction in format YYYY-MM-DD or DD-MM-YYYY (e.g., 2026-07-08).
    - time: Time of the interaction in 24h format HH:MM.
    - interaction_type: Type of interaction (e.g., Meeting, Email, Call, Event).
    - sentiment: Observed HCP sentiment (Positive, Neutral, Negative).
    - topics_discussed: Summary of the topics discussed.
    - outcomes: Key outcomes or agreements from the meeting.
    - follow_up_actions: Follow up actions or next steps.
    - attendees: List of names attending the meeting.
    """
    data = {
        "hcp_name": hcp_name,
        "date": date or "",
        "time": time or "",
        "interaction_type": interaction_type or "Meeting",
        "sentiment": sentiment or "Neutral",
        "topics_discussed": topics_discussed or "",
        "outcomes": outcomes or "",
        "follow_up_actions": follow_up_actions or "",
        "attendees": attendees or []
    }
    
    # Try to verify HCP against database
    db = get_db_session()
    try:
        db_hcp = db.query(HCP).filter(HCP.name.like(f"%{hcp_name}%")).first()
        if db_hcp:
            data["hcp_name"] = db_hcp.name  # Use exact name from DB
            # If attendees is empty, add the HCP and a default sales rep
            if not data["attendees"]:
                data["attendees"] = [db_hcp.name, "Rep (Me)"]
    except Exception as e:
        print(f"Error querying HCP in log_interaction: {e}")
    finally:
        db.close()
        
    return json.dumps(data)

@tool
def edit_interaction(field_name: str, new_value: Any) -> str:
    """
    Updates a specific field in the logged interaction data when a user specifies a correction.
    Arguments:
    - field_name: The name of the form field to edit. Must be one of:
      'hcp_name', 'interaction_type', 'date', 'time', 'attendees', 'topics_discussed', 
      'sentiment', 'outcomes', 'follow_up_actions'.
    - new_value: The new value to set. For 'attendees', this should be a list of strings, for others a string.
    """
    # Canonicalize field name
    field_map = {
        "hcp": "hcp_name",
        "hcp name": "hcp_name",
        "name": "hcp_name",
        "type": "interaction_type",
        "date": "date",
        "time": "time",
        "attendees": "attendees",
        "topics": "topics_discussed",
        "topics discussed": "topics_discussed",
        "sentiment": "sentiment",
        "outcomes": "outcomes",
        "follow_up": "follow_up_actions",
        "followup": "follow_up_actions",
        "follow-up": "follow_up_actions"
    }
    
    canonical_field = field_map.get(field_name.lower(), field_name)
    
    # Capitalize sentiment values correctly
    if canonical_field == "sentiment" and isinstance(new_value, str):
        new_value = new_value.strip().capitalize()
        if new_value not in ["Positive", "Neutral", "Negative"]:
            new_value = "Neutral"

    return json.dumps({
        "field": canonical_field,
        "value": new_value
    })

@tool
def search_materials_and_samples(query: str, category: str) -> str:
    """
    Searches the product catalog database for materials (brochures, slide decks, PDFs) or product samples (starter kits, sample packs)
    to add them to the shared lists.
    Arguments:
    - query: Name or product keywords (e.g. 'Onco', 'Cardio', 'brochure').
    - category: The type of list to search, either 'material' or 'sample'.
    """
    db = get_db_session()
    results = []
    try:
        if category.lower() == "material":
            items = db.query(Material).filter(
                (Material.name.like(f"%{query}%")) | (Material.product.like(f"%{query}%"))
            ).all()
            results = [{"name": item.name, "type": item.type, "product": item.product} for item in items]
        else:
            items = db.query(Sample).filter(
                (Sample.name.like(f"%{query}%")) | (Sample.product.like(f"%{query}%"))
            ).all()
            results = [{"name": item.name, "dosage": item.dosage, "product": item.product} for item in items]
    except Exception as e:
        print(f"Error searching materials/samples: {e}")
    finally:
        db.close()
        
    return json.dumps({
        "category": category.lower(),
        "query": query,
        "results": results
    })

@tool
def get_hcp_profile(hcp_name: str) -> str:
    """
    Queries the CRM database to retrieve detailed profile information, specialty, email, phone, and past interaction history
    notes for a specific Healthcare Professional.
    Arguments:
    - hcp_name: The name of the doctor (e.g., 'Dr. Smith', 'Sharma').
    """
    db = get_db_session()
    try:
        # Fuzzy match
        hcp = db.query(HCP).filter(HCP.name.like(f"%{hcp_name}%")).first()
        if hcp:
            profile = {
                "name": hcp.name,
                "specialty": hcp.specialty,
                "organization": hcp.organization,
                "email": hcp.email,
                "phone": hcp.phone,
                "history_notes": hcp.history_notes
            }
            return json.dumps({"found": True, "profile": profile})
        else:
            return json.dumps({"found": False, "message": f"No HCP profile found matching name '{hcp_name}'."})
    except Exception as e:
        return json.dumps({"found": False, "error": str(e)})
    finally:
        db.close()

@tool
def generate_follow_up_tasks(discussion_topics: str) -> str:
    """
    Analyzes the topics discussed during the interaction to suggest specific actionable next steps and follow-ups.
    Arguments:
    - discussion_topics: Key points covered during the meeting.
    """
    suggestions = []
    topics_lower = discussion_topics.lower()
    
    # Rule-based suggestions to ensure quick and deterministic matches if Groq has hiccups
    if "oncoboost" in topics_lower or "efficiency" in topics_lower:
        suggestions.append("Send OncoBoost Phase III PDF")
        suggestions.append("Schedule follow-up meeting in 2 weeks")
    if "cardioshield" in topics_lower or "safety" in topics_lower or "brochure" in topics_lower:
        suggestions.append("Deliver CardioShield 5mg Patient Sample pack")
        suggestions.append("Email CardioShield clinical trial booklet")
    if "sharma" in topics_lower or "advisory" in topics_lower or "board" in topics_lower:
        suggestions.append("Add Dr. Sharma to advisory board invite list")
    
    # Generic fallbacks if nothing matched
    if not suggestions:
        suggestions.append("Schedule follow-up email in 1 week")
        suggestions.append("Update physician preference profile in CRM")
        
    return json.dumps({
        "suggestions": suggestions
    })

# Package all tools
tools_list = [
    log_interaction,
    edit_interaction,
    search_materials_and_samples,
    get_hcp_profile,
    generate_follow_up_tasks
]
