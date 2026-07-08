from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table
from sqlalchemy.orm import relationship
from .database import Base

class HCP(Base):
    __tablename__ = "hcps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    specialty = Column(String(100), nullable=True)
    organization = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    history_notes = Column(Text, nullable=True)  # Past interactions summary for context

    interactions = relationship("Interaction", back_populates="hcp")

class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False)
    type = Column(String(50), nullable=False)  # Brochure, Slide Deck, PDF
    product = Column(String(100), nullable=False)

class Sample(Base):
    __tablename__ = "samples"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False)
    product = Column(String(100), nullable=False)
    dosage = Column(String(50), nullable=True)

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcps.id"), nullable=False)
    date = Column(String(50), nullable=True)
    time = Column(String(50), nullable=True)
    interaction_type = Column(String(50), nullable=True)  # Meeting, Email, Call, etc.
    attendees = Column(Text, nullable=True)               # JSON string of lists
    topics_discussed = Column(Text, nullable=True)
    sentiment = Column(String(20), nullable=True)         # Positive, Neutral, Negative
    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)
    materials_shared = Column(Text, nullable=True)         # JSON string list
    samples_distributed = Column(Text, nullable=True)      # JSON string list

    hcp = relationship("HCP", back_populates="interactions")

class SuggestedFollowUp(Base):
    __tablename__ = "suggested_follow_ups"

    id = Column(Integer, primary_key=True, index=True)
    hcp_name = Column(String(100), nullable=False)
    text = Column(String(500), nullable=False)
    status = Column(String(20), default="Pending")         # Pending, Added, Dismissed
