import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GROQ_API_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./hcp_crm.db"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
