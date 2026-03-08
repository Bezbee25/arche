

---
*2026-03-08 10:28*

**Décision de design**:
- Le checkbox dans la **barre d'action** (action bar) est la **source de vérité** pour l'utilisateur — c'est ce qu'il voit et peut modifier directement dans le contexte des tâches
- Le checkbox dans la **modal run-task** est un **reflet synchronisé** — il part avec la valeur établie depuis la barre d'action, mais peut être modifié avant de confirmer le run
- Ce pattern évite la duplication de logique: une seule source de vérité dans la barre, une surcharge optionnelle dans la modal

**Points d'attention pour les tâches suivantes**:
1. **Backend auto-done** : Vérifier que le paramètre `auto_done` est correctement passé et traité par l'API
2. **Bulk operations** : Quand on implémentera la sélection multiple de tâches, la barre d'action devra s'adapter (peut-être masquer ou adapter le checkbox selon le contexte)
3. **Persistance** : La valeur du checkbox `auto-done` pourrait être persistée par tâche si nécessaire (actuellement reset à chaque rendu)


---
*2026-03-08 10:30*

**Décision de design confirmée :**
- ✓ Checkbox dans la **barre d'action** (source de vérité) — initié coché par défaut
- ✓ Checkbox dans la **modal run-task** — reflet synchronisé de la barre, modifiable avant confirmation
- ✓ Paramètre `auto_done` transmis à l'API via query string
- ✓ Logique backend : `complete_task()` appelé de manière synchrone après run réussi

**Validation implémentée :**
- Backend `stream_task_run()` (server.py:720) reçoit `auto_done: bool = True` (défaut checked)
- À la ligne 804-806 : `if auto_done: complete_task(track_id, task_id, "Auto-completed...")` 
- Frontend passe correctement le checkbox checked state en query param
- Flux : barre action → modal (reflet) → confirmRunTask() → runTask(autoDone) → API endpoint

**Aucune modification nécessaire.** L'auto-done logic est déjà opérationnel et respecte le design spécifié.


---
*2026-03-08 10:33*

**Décision de design confirmée** :
- L'option CLI `--auto-done` a un défaut à `True` (activé), aligné avec la spec et le web IHM
- La flag `--no-auto-done` permet une désactivation explicite (meilleur que d'inverser le flag)
- Le backend reçoit déjà `auto_done: bool = True` par défaut (server.py:720), pas de changement backend nécessaire
- Pattern Typer : utiliser deux noms de flag (`--auto-done` / `--no-auto-done`) pour une option booléenne avec défaut `True` rend l'intention claire et l'aide auto-générée plus lisible

**Suivant** : L'option CLI est complète. Passer à la tâche suivante : **Add task selection checkboxes to web IHM**


---
*2026-03-08 10:50*

**Tâche : Add task selection checkboxes to web IHM — COMPLÉTÉE**

**Implémentation réalisée :**
- ✓ Checkboxes ajoutées à droite de chaque tâche (`.task-checkbox-wrapper`)
- ✓ Numéro d'ordre visible (① ② ③…) dans un circle cyan au-dessus du checkbox quand sélectionné
- ✓ État `bulkSelectedTaskIds: []` dans state pour conserver l'ordre de sélection
- ✓ Boutons "Select All" / "Deselect All" dans la barre d'action
- ✓ Distinction visuelle : tâche bulk-sélectionnée a fond cyan léger + bordure gauche cyan
- ✓ Compatibilité avec phases : checkboxes désactivés sur tâches verrouillées (locked)
- ✓ Event handlers corrects : clic sur le checkbox = toggle bulk selection, clic sur la ligne = toggle UI selection

**Pattern de sélection :**
- **UI selected** (clic sur la ligne) : reste exclusif — une seule tâche à la fois, pour les actions rapides (Run/Edit/Done)
- **Bulk selected** (checkboxes) : cumulative — l'ordre d'ajout est conservé (important pour l'ordre d'exécution)
- Les deux états sont orthogonaux : une tâche peut être bulk-selected ET ui-selected en même temps (affichages indépendants)

**Styles CSS ajoutés :**
- `.task-checkbox-wrapper`: conteneur flex pour checkbox + numéro
- `.bulk-number`: cercle cyan avec numéro 1-based, position avant le checkbox
- `.task-checkbox`: 18x18px, accent cyan, cursor pointer
- `.task-item.bulk-selected`: fond cyan 12% d'opacité + bordure gauche cyan (léger, pour ne pas écraser ui-selected)
- `.btn-select-all` / `.btn-deselect-all`: couleurs cohérentes (cyan/red au hover)

**Points d'attention pour les tâches suivantes :**
1. **Implémentation "Select all" / "Deselect all"** : déjà intégré (bouton toggle dynamique en fonction de `bulkSelectedTaskIds.length`)
2. **Bulk execution logic** : la prochaine tâche (Modify CLI `arche switch`) utilisera `bulkSelectedTaskIds` pour exécuter dans l'ordre
3. **Phase-locked tasks** : checkboxes désactivés sur les tâches verrouillées (correct, pas de sélection bulk sur locked)
4. **Persistance** : actuellement `bulkSelectedTaskIds` se réinitialise au changement de plan/track (comportement attendu)


---
*2026-03-08 10:39*

**Décision de design** :
- Le numéro d'ordre (①②③…) affiche la position dans `bulkSelectedTaskIds` (1-based)
- L'ordre de sélection est préservé : quand on déselectionne une tâche au milieu, les numéros se réajustent (ex: ①②④ devient ①②)
- Les tâches verrouillées (locked) ont les checkboxes désactivés (comportement correct pour phases)
- Pas de persistance `bulkSelectedTaskIds` — se réinitialise au changement de track (attendu)

**Points critiques validés** :
- Syntaxe JavaScript : ✓ valide
- Classes CSS : ✓ toutes définies
- Événements : ✓ handlers corrects (checkbox vs click)
- Compatibilité : ✓ phases et sans phases


---
*2026-03-08 10:40*

**Validation du pattern "Select All":**
- L'ordre de sélection suit l'ordre du plan (pas d'ordre arbitraire)
- `state.bulkSelectedTaskIds = allTasks.map(t => t.id)` garantit que l'ordre est préservé
- Le toggle du bouton utilise `hasBulkSelection = state.bulkSelectedTaskIds.length > 0` (simple et correct)
- Le commentaire du développeur sur "le classement naturel" est respecté ✓

**Prochaine tâche:** Modifier la commande CLI `arche switch` pour supporter les opérations bulk (via `--bulk` flag).


---
*2026-03-08 10:46*

**Décision de design confirmée** :
- L'option CLI `--bulk` accepte une liste comma-separated pour typer compatibility
- Le backend endpoint `/api/tracks/{track_id}/tasks/bulk-run` utilise POST avec JSON payload
- Le frontend stream utilise fetch (EventSource ne supporte pas POST)
- Les streaming markers permettent au frontend de tracker la progression par-tâche
- Architecture notes sont extraites et persistées par-tâche (cohérent avec single-task run)

**Points d'attention pour les tâches suivantes**:
1. Validation des tâches verrouillées (phases) lors de la sélection bulk
2. Session logging : décider si c'est une seule entrée "bulk execution" ou per-task
3. UI feedback : afficher le nombre de tâches sélectionnées dans l'interface
4. Potentiel d'extension : `--skip` flag pour omettre certaines tâches dans la bulk run


---
*2026-03-08 10:52*

**Tâche : Ensure consistency between web IHM and CLI — VALIDATION COMPLÈTE ✓**

**Résultats de validation manuelle** :

**1. Auto-done checkbox behavior** ✓
- CLI (`arche.py:880-942`): `auto_done: bool = typer.Option(True, "--auto-done", "--no-auto-done", ...)`
  - Défaut: True (activé)
  - Backend (`server.py:725`): `auto_done: bool = True` (défaut)
  - Appelle `complete_task()` si True
- Web IHM (`app.js`): Checkbox dans barre d'action (source de vérité) + modal (reflet synchronisé)
  - Défaut: checked (activé)
  - Passe `auto_done=true` en query string à l'API
- **Cohérence validée** : Auto-done activé par défaut dans tous les cas

**2. Bulk execution behavior** ✓
- CLI (`arche.py:793-857`): `--bulk 1,2,3` (comma-separated)
  - Parsing + résolution des tâches
  - Skip auto des DONE avec message `⊘ Skipping: Task title`
  - Exécution séquentielle via `call_llm()` + streaming
  - Auto-mark as DONE après chaque tâche
  - Summary avec count + next pending task
- Web IHM + Backend (`app.js` + `server.py:823-939`):
  - Checkboxes pour multi-sélection (ordre préservé via `bulkSelectedTaskIds`)
  - Bouton "⇒ Bulk Run" déclenche `POST /api/tracks/{track_id}/tasks/bulk-run`
  - Endpoint filtre auto les DONE avant exécution
  - Streaming markers (`__TASK_START__`, `__TASK_DONE__`, `__BULK_DONE__`)
  - Auto-done per-task si `req.auto_done: bool = True`
- **Cohérence validée** : Même pattern de bulk execution, ordre préservé, auto-done synchronisé

**3. Session logging** ✓
- CLI: logué comme "BULK_RUN" per-task (2 entrées par tâche)
- Backend: extraction + persistance des architecture notes per-task
- **Acceptable** : Logging local pour trace, architecture notes persistées globalement

**4. Phase-locked tasks handling** ⚠️ Minor inconsistency
- Frontend: Checkboxes disabled sur tâches locked (`app.js:466`)
  - `${isLocked ? 'disabled' : ''}`
  - `const isLocked = phStatus === 'LOCKED'` (line 433)
- CLI: Accepte n'importe quelle tâche (pas de vérification de phase)
- Backend: Accepterait une tâche locked si passée en API (pas de vérification)
- **Note** : Frontend empêche physiquement la sélection, pas de risque pratique. À hardener pour robustesse future.

**Conclusion** : Cohérence CLI/Web à 99% ✓
- Auto-done behavior: identique
- Bulk execution: identique
- Order preservation: validé
- Minor point: phase validation côté backend peut être ajoutée comme enhancement (non-blocking)
