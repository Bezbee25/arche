"""
Instruction storage and management.
"""
import json
from pathlib import Path
from typing import List, Optional, Dict
from models.instruction import Instruction, InstructionManifest


class InstructionStore:
    """Stores and manages instruction templates."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize the instruction store.
        
        Args:
            storage_path: Path to the instructions directory. 
                        Defaults to .arche-storage/instructions
        """
        if storage_path is None:
            storage_path = Path(".arche-storage/instructions")
        
        self.storage_path = storage_path
        self.manifest_path = storage_path / "manifest.json"
        
        # Create storage directory if it doesn't exist
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def load_manifest(self) -> InstructionManifest:
        """Load the instruction manifest from disk."""
        if not self.manifest_path.exists():
            return InstructionManifest(instructions=[])
        
        try:
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return InstructionManifest(**data)
        except (json.JSONDecodeError, FileNotFoundError):
            return InstructionManifest(instructions=[])
    
    def save_manifest(self, manifest: InstructionManifest) -> None:
        """Save the instruction manifest to disk."""
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.dict(), f, indent=2, ensure_ascii=False)
    
    def get_all_instructions(self) -> List[Instruction]:
        """Get all instructions from the manifest."""
        manifest = self.load_manifest()
        return manifest.instructions
    
    def get_instruction(self, instruction_id: str) -> Optional[Instruction]:
        """Get a specific instruction by ID."""
        manifest = self.load_manifest()
        for instruction in manifest.instructions:
            if instruction.id == instruction_id:
                return instruction
        return None
    
    def add_instruction(self, instruction: Instruction) -> None:
        """Add a new instruction to the manifest."""
        manifest = self.load_manifest()
        
        # Check if instruction already exists
        for existing in manifest.instructions:
            if existing.id == instruction.id:
                raise ValueError(f"Instruction with id '{instruction.id}' already exists")
        
        manifest.instructions.append(instruction)
        self.save_manifest(manifest)
    
    def update_instruction(self, instruction: Instruction) -> None:
        """Update an existing instruction."""
        manifest = self.load_manifest()
        
        for i, existing in enumerate(manifest.instructions):
            if existing.id == instruction.id:
                manifest.instructions[i] = instruction
                self.save_manifest(manifest)
                return
        
        raise ValueError(f"Instruction with id '{instruction.id}' not found")
    
    def delete_instruction(self, instruction_id: str) -> None:
        """Delete an instruction by ID."""
        manifest = self.load_manifest()
        
        manifest.instructions = [
            inst for inst in manifest.instructions 
            if inst.id != instruction_id
        ]
        
        self.save_manifest(manifest)
    
    def enable_instruction(self, instruction_id: str, enabled: bool) -> None:
        """Enable or disable an instruction."""
        manifest = self.load_manifest()
        
        for inst in manifest.instructions:
            if inst.id == instruction_id:
                inst.is_enabled = enabled
                self.save_manifest(manifest)
                return
        
        raise ValueError(f"Instruction with id '{instruction_id}' not found")
    
    def search_instructions(
        self, 
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Instruction]:
        """Search instructions by query, category, and/or tags."""
        manifest = self.load_manifest()
        results = []
        
        for instruction in manifest.instructions:
            # Filter by category
            if category and instruction.category != category:
                continue
            
            # Filter by tags
            if tags and not any(tag in instruction.tags for tag in tags):
                continue
            
            # Filter by query (search in name and description)
            if query:
                query_lower = query.lower()
                if (query_lower not in instruction.name.lower() and 
                    query_lower not in instruction.description.lower()):
                    continue
            
            results.append(instruction)
        
        return results
