"""Developer agent: delegate code generation to the right LLM with full context."""
from __future__ import annotations

from rich.console import Console

from core.context import build_task_prompt, extract_archi_notes, append_archi
from core.track_manager import get_spec
from core.router import call_llm
from core.session_logger import log
from core.task_engine import get_current_task

console = Console()


def run(track_id: str, track_meta: dict, instruction: str) -> str:
    """Delegate a coding task to the LLM with full plan context."""
    spec = get_spec(track_id)
    current_task = get_current_task(track_id)

    # Base : contexte complet du plan
    base_prompt = build_task_prompt(track_id, track_meta)

    # Ajouter l'instruction spécifique par-dessus
    prompt = (
        f"{base_prompt}\n\n"
        f"---\n"
        f"**Instruction supplémentaire :** {instruction}"
    )

    console.print(f"\n[bold cyan]Developer[/bold cyan] — phase: {track_meta.get('phase', 'dev')}\n")
    log(track_id, f"Dev: {instruction[:80]}", "DEV")

    result = call_llm(prompt, phase="dev", track_meta=track_meta, stream=True)

    # Sauvegarder les notes d'architecture si présentes
    archi_notes = extract_archi_notes(result)
    if archi_notes:
        append_archi(track_id, archi_notes)
        console.print(f"\n[green]✓ Notes d'architecture mises à jour.[/green]")

    return result
