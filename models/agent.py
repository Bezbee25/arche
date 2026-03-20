from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class Agent(BaseModel):
    id: str
    name: str
    role: str
    description: str
    system_prompt: str
    model: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AgentManifest(BaseModel):
    agents: list[Agent]
    version: str = "1.0.0"
