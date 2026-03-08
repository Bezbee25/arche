# Spec: amélioration gestion des tasks

## Goal
Implement enhanced task management capabilities including bulk operations and automatic status updates.

## Context
Currently, task status updates (development and done) are performed manually on an individual basis. The system lacks bulk operations and automatic status transitions. The web IHM and CLI need to support these new workflows while maintaining simplicity and consistency.

## Requirements

1. **Auto-done functionality**
   - Add a checkbox in the web IHM next to each run that enables automatic task status update to "done" upon run completion
   - Add a CLI option `--auto-done` (or similar) to enable this behavior
   - Default behavior: checkbox checked by default in web IHM, auto-done enabled by default in CLI
   - Acceptance: Task status automatically transitions to "done" when run completes with auto-done enabled

2. **Bulk task selection and execution**
   - Add checkboxes to the right of each task in the web IHM to enable multi-task selection
   - Implement a "Select all" / "Deselect all" toggle in the web IHM
   - Modify the CLI `arche switch` command to support bulk operations with a `--bulk` flag
   - Default behavior: single task selection only (no bulk operations by default)
   - Acceptance: Multiple tasks can be selected and executed together via both web IHM and CLI

## Constraints
- Do not modify existing track structures or functionality
- Changes must be limited to task management features
- Implementations in web IHM and CLI must maintain consistency
- Keep user interface simple and intuitive
- No additional testing required (developer will handle testing)

## Out of Scope
- Track-level modifications
- Additional test coverage
- Audit documentation beyond what's already in track's audit.md
- Features beyond auto-done and bulk operations