"""Compatibility shim — plan_manager is now track_manager."""
from core.track_manager import *  # noqa: F401, F403
from core.track_manager import (
    TRACKS_DIR as PLANS_DIR,
    get_current_track_id as get_current_plan_id,
    set_current_track_id as set_current_plan_id,
    get_active_track as get_active_plan,
    list_tracks as list_plans,
    get_track as get_plan,
    new_track as new_plan,
    switch_track as switch_plan,
    mark_track_done as mark_plan_done,
    update_track_phase as update_plan_phase,
    update_track_meta as update_plan_meta,
)
