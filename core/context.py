"""Construction du contexte riche à passer au LLM pour une tâche."""
from __future__ import annotations

from pathlib import Path

from core.track_manager import (
    TRACKS_DIR,
    get_spec,
    load_project,
    load_yaml,
)
from core.scanner import get_global_archi, get_global_memory, GLOBAL_MEMORY_PATH
from core.session_logger import get_session_log, list_sessions
from core.task_engine import STATUS_DONE, STATUS_IN_PROGRESS, STATUS_TODO, load_tasks


def _archi_path(track_id: str) -> Path:
    return TRACKS_DIR / track_id / "archi.md"


def get_archi(track_id: str) -> str:
    path = _archi_path(track_id)
    return path.read_text() if path.exists() else ""


def append_archi(track_id: str, notes: str) -> None:
    """Ajoute des notes à archi.md (crée le fichier si besoin)."""
    from datetime import datetime
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    path = _archi_path(track_id)
    header = f"\n\n---\n*{now}*\n\n"
    with open(path, "a") as f:
        f.write(header + notes.strip() + "\n")
    # Propagate to global cross-track memory
    memory_header = f"\n\n---\n*{now}* | track: {track_id}\n\n"
    GLOBAL_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GLOBAL_MEMORY_PATH, "a") as f:
        f.write(memory_header + notes.strip() + "\n")


def build_task_prompt(track_id: str, track_meta: dict, comment: str = "") -> str:
    """Construit le prompt complet pour exécuter la tâche courante."""
    project = load_project()
    tasks = load_tasks(track_id)
    spec = get_spec(track_id)
    global_archi = get_global_archi()
    global_memory = get_global_memory()
    archi = get_archi(track_id)

    # Tâche courante
    current = next((t for t in tasks if t["status"] == STATUS_IN_PROGRESS), None)
    if not current:
        current = next((t for t in tasks if t["status"] == STATUS_TODO), None)

    # Tâches terminées
    done_tasks = [t for t in tasks if t["status"] == STATUS_DONE]
    pending_tasks = [t for t in tasks if t["status"] not in (STATUS_DONE, STATUS_IN_PROGRESS)]

    # Session récente (aujourd'hui ou hier)
    sessions = list_sessions(track_id)
    recent_log = ""
    if sessions:
        recent_log = get_session_log(track_id, sessions[0])[:1500]

    # ── Assemblage du prompt ───────────────────────────────────────────────
    parts = []

    parts.append(
        f"Tu es un agent de développement travaillant sur le projet **{project.get('name', track_id)}**.\n"
        f"Stack : {project.get('stack', 'non précisé')}\n"
        f"Track courant : **{track_meta.get('name', track_id)}**\n"
    )

    protected_paths = project.get("protected_paths", [])
    if protected_paths:
        paths_list = "\n".join(f"  - {p}" for p in protected_paths)
        parts.append(
            f"## CHEMINS PROTÉGÉS — LECTURE SEULE\n\n"
            f"Tu peux lire ces fichiers/répertoires pour contexte, "
            f"mais tu NE DOIS EN AUCUN CAS les modifier (ni Write, ni Edit) :\n\n"
            f"{paths_list}"
        )

    if spec and spec.strip():
        parts.append(f"## Spec du track\n\n{spec}")

    if global_archi and global_archi.strip():
        parts.append(f"## Architecture du projet (référence globale)\n\n{global_archi}")

    if global_memory and global_memory.strip():
        parts.append(f"## Mémoire partagée (découvertes cross-track)\n\n{global_memory}")

    if archi and archi.strip():
        parts.append(f"## Notes d'architecture du track\n\n{archi}")

    if done_tasks:
        done_parts = []
        for t in done_tasks:
            entry = f"✓ **{t['title']}**"
            if t.get("notes"):
                entry += f"\n   Findings: {t['notes']}"
            done_parts.append(entry)
        done_list = "\n\n".join(done_parts)
        parts.append(
            f"## Tâches déjà complétées\n\n"
            f"⚠ Ces tâches sont TERMINÉES. Leurs findings sont listés ci-dessous — "
            f"ne les répète pas, utilise directement ces résultats.\n\n"
            f"{done_list}"
        )

    if current:
        task_block = f"**{current['title']}**"
        if current.get("description"):
            task_block += f"\n\n{current['description']}"
        if current.get("notes"):
            task_block += f"\n\nNotes existantes : {current['notes']}"
        parts.append(f"## Tâche courante (à exécuter)\n\n{task_block}")

    if pending_tasks:
        pending_list = "\n".join(f"  · {t['title']}" for t in pending_tasks)
        parts.append(f"## Tâches suivantes (pour contexte)\n\n{pending_list}")

    if recent_log:
        parts.append(f"## Journal de session récent\n\n{recent_log}")

    if comment and comment.strip():
        parts.append(f"## Commentaire du développeur\n\n{comment.strip()}")

    parts.append(
        "---\n"
        "Exécute la tâche courante. Sois concret et actionnable.\n\n"
        "**IMPORTANT** : Si des tâches précédentes ont déjà effectué une analyse ou un audit, "
        "leurs résultats sont dans les sections 'Tâches déjà complétées' et 'Notes d'architecture du track'. "
        "Utilise ces informations directement — ne refais pas une analyse déjà faite.\n\n"
        "À la fin de ta réponse, ajoute impérativement une section :\n\n"
        "## Notes d'architecture\n"
        "*(Pour les tâches d'analyse/audit : résume tous les findings clés, localisations précises, bugs trouvés.*\n"
        "*Pour les tâches d'implémentation : décisions prises, patterns, changements effectués.*\n"
        "*Toujours inclure les infos utiles pour les tâches suivantes.)*\n"
        "Si rien à noter, écris : `(aucune note)`"
    )

    return "\n\n".join(parts)


def extract_archi_notes(llm_output: str) -> str | None:
    """Extrait la section '## Notes d'architecture' de la sortie LLM."""
    marker = "## Notes d'architecture"
    idx = llm_output.find(marker)
    if idx == -1:
        # Essai en anglais
        marker = "## Architecture notes"
        idx = llm_output.find(marker)
    if idx == -1:
        return None
    notes = llm_output[idx + len(marker):].strip()
    if not notes or notes.lower().startswith("(aucune") or notes.lower().startswith("(none"):
        return None
    return notes
