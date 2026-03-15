"""
Instruction models for storing and managing instruction templates.
"""
from typing import List, Optional
from pydantic import BaseModel
from enum import Enum


class InstructionCategory(str, Enum):
    GENERAL = "general"
    LANGUAGES = "languages"
    FRONTEND = "frontend"
    BACKEND = "backend"
    TOOLING = "tooling"


class InstructionSource(str, Enum):
    BUILTIN = "builtin"
    USER = "user"
    EXTERNAL = "external"


class Instruction(BaseModel):
    id: str
    name: str
    description: str
    category: InstructionCategory
    tags: List[str] = []
    content: str
    source: InstructionSource
    source_url: Optional[str] = None
    license: Optional[str] = None
    is_enabled: bool = True


class InstructionManifest(BaseModel):
    instructions: List[Instruction]
    version: str = "1.0.0"
