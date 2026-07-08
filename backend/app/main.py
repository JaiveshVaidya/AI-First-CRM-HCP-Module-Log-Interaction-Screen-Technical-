import json
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from .database import engine, Base, get_db
from .config import settings
from . import models, schemas
from .agent import run_chat_agent

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI-First CRM HCP Module API",
    description="Backend API for managing HCP interactions via conversational chat and structured logging.",
    version="1.0.0"
)

# Configure CORS for React/Vite development server (default port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, lock this down
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "model": "gemma2-9b-it", "api_key_configured": bool(settings.GROQ_API_KEY)}

@app.get("/api/hcps", response_model=List[schemas.HCPOut])
def get_hcps(db: Session = Depends(get_db)):
    return db.query(models.HCP).all()

@app.get("/api/materials", response_model=List[schemas.MaterialOut])
def get_materials(db: Session = Depends(get_db)):
    return db.query(models.Material).all()

@app.get("/api/samples", response_model=List[schemas.SampleOut])
def get_samples(db: Session = Depends(get_db)):
    return db.query(models.Sample).all()

@app.post("/api/chat", response_model=schemas.ChatResponse)
def chat_interaction(request: schemas.ChatRequest):
    """
    Receives user message and current form state, runs the LangGraph AI Agent,
    and returns assistant reply, updated form, and suggestions.
    """
    try:
        # We don't maintain direct chat history in database sessions for simplicity;
        # instead, we let the frontend send or manage the active conversation session.
        # Here we run our LangGraph runner
        result = run_chat_agent(
            message=request.message,
            current_form=request.current_form.dict(),
            chat_history=[] # For stateless execution per request, or can expand to session history
        )
        
        return schemas.ChatResponse(
            message=result["message"],
            form_data=schemas.FormFields(**result["form_data"]),
            suggested_follow_ups=result["suggested_follow_ups"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent Error: {str(e)}"
        )

@app.post("/api/interactions")
def log_interaction_record(interaction: schemas.InteractionCreate, db: Session = Depends(get_db)):
    """
    Saves the final logged interaction to the SQL database.
    """
    try:
        # Find the HCP
        hcp = db.query(models.HCP).filter(models.HCP.name == interaction.hcp_name).first()
        if not hcp:
            # Create a new HCP profile on-the-fly if it doesn't exist
            hcp = models.HCP(
                name=interaction.hcp_name,
                specialty="General Medicine",
                organization="Unknown Clinic",
                history_notes="First logged interaction."
            )
            db.add(hcp)
            db.commit()
            db.refresh(hcp)
            
        # Create interaction log
        db_interaction = models.Interaction(
            hcp_id=hcp.id,
            date=interaction.date,
            time=interaction.time,
            interaction_type=interaction.interaction_type,
            attendees=json.dumps(interaction.attendees),
            topics_discussed=interaction.topics_discussed,
            sentiment=interaction.sentiment,
            outcomes=interaction.outcomes,
            follow_up_actions=interaction.follow_up_actions,
            materials_shared=json.dumps(interaction.materials_shared),
            samples_distributed=json.dumps(interaction.samples_distributed)
        )
        db.add(db_interaction)
        db.commit()
        db.refresh(db_interaction)
        
        # Save suggested followups in db
        for follow_up in interaction.ai_suggested_follow_ups:
            db_followup = models.SuggestedFollowUp(
                hcp_name=interaction.hcp_name,
                text=follow_up,
                status="Added"
            )
            db.add(db_followup)
            
        db.commit()
        
        return {
            "status": "success",
            "message": "Interaction logged and saved to CRM database successfully.",
            "interaction_id": db_interaction.id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database Write Error: {str(e)}"
        )
