

---
*2026-03-07 19:29* | track: theme-task-dev

- **Theme key scoping**: La clé localStorage est `arche-theme-<projectName>` où `projectName` vient de `/api/project`. L'early-apply script dans `<head>` itère sur toutes les clés `arche-theme-*` pour trouver la plus récente, ce qui fonctionne bien en pratique (une session browser = un projet).
- **xterm.js theme update**: `term.options.theme = {...}` fonctionne avec xterm.js 5.x pour mettre à jour le thème en live sans recréer le terminal. Les couleurs ANSI du contenu existant ne changent pas (elles sont rendues en bitmap), seul le background/foreground/cursor change immédiatement.
- **Hard-coded colors**: Plusieurs couleurs étaient hard-codées dans le CSS original (`#252525`, `#1a2a1a`, etc.). Elles ont été remplacées par des variables CSS — point d'attention pour toute future couleur ajoutée dans le CSS.
- **Flash prevention**: Le script inline `<head>` couvre le cas où la page charge avec un thème non-Dark. Il relit les palettes dupliquées (légère redondance avec `THEMES` dans app.js) — acceptable car les données sont petites et cette approche évite tout FOUC sans dépendance à l'ordre de chargement des scripts.


---
*2026-03-07 19:38* | track: theme-task-dev

- **Cause racine du bug** : les listeners du bouton Theme étaient enregistrés dans `setupTheme()`, qui était appelé **après** un `await api.getProject()` dans `init()`. Si `setupTerminal()` (appelé juste avant le `await`) levait une exception — notamment si xterm.js (CDN) n'était pas encore chargé — l'exception interrompait `init()` et `setupTheme()` n'était jamais atteint. Résultat : `btn-theme` n'avait aucun listener.

- **Pattern à retenir** : les `addEventListener` sur des éléments UI statiques (boutons présents dans le HTML dès le chargement) doivent être enregistrés dans `setupEventListeners()` (synchrone), **pas** dans des fonctions appelées après un `await`. Ne jamais dépendre d'une réponse réseau pour enregistrer des listeners de base.

- **Guard ajouté** : `try/catch` autour de `setupTerminal()` pour isoler les erreurs xterm.js des autres initialisations.


---
*2026-03-07 19:46* | track: theme-task-dev

- **Stacking context & flex order** : dans un flex container sans z-index explicite, les éléments sont empilés dans l'ordre DOM. Un élément avec `overflow: hidden` (comme `#main`) crée un stacking context et peut masquer un dropdown `position: absolute` qui dépasse d'un élément frère précédent dans le DOM (`#header`). Toujours donner un `z-index` explicite à un header qui contient des dropdowns.
- **Pattern général** : tout composant header/navbar contenant un dropdown doit avoir `position: relative; z-index: N` pour se garantir d'être au-dessus du contenu principal.
- **Le JS était correct** — le listener du bouton, le toggle de la classe `.hidden`, les `window.applyTheme` / `window.closeThemeDropdown` exposés globalement, tout fonctionnait. Le bug était purement CSS/stacking.


---
*2026-03-07 21:17* | track: taille-icone

- Augmentation de la taille des icônes dans les boutons via `.btn-icon` (17px → 34px)
- Remplacement des caractères Unicode pour les icônes "Refresh" et "Documentation" par des variantes plus visibles
- Pas de modification structurelle, uniquement ajustement visuel


---
*2026-03-08 10:28* | track: amélioration-gestion-des-tasks

**Décision de design**:
- Le checkbox dans la **barre d'action** (action bar) est la **source de vérité** pour l'utilisateur — c'est ce qu'il voit et peut modifier directement dans le contexte des tâches
- Le checkbox dans la **modal run-task** est un **reflet synchronisé** — il part avec la valeur établie depuis la barre d'action, mais peut être modifié avant de confirmer le run
- Ce pattern évite la duplication de logique: une seule source de vérité dans la barre, une surcharge optionnelle dans la modal

**Points d'attention pour les tâches suivantes**:
1. **Backend auto-done** : Vérifier que le paramètre `auto_done` est correctement passé et traité par l'API
2. **Bulk operations** : Quand on implémentera la sélection multiple de tâches, la barre d'action devra s'adapter (peut-être masquer ou adapter le checkbox selon le contexte)
3. **Persistance** : La valeur du checkbox `auto-done` pourrait être persistée par tâche si nécessaire (actuellement reset à chaque rendu)


---
*2026-03-08 10:30* | track: amélioration-gestion-des-tasks

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
*2026-03-08 10:33* | track: amélioration-gestion-des-tasks

**Décision de design confirmée** :
- L'option CLI `--auto-done` a un défaut à `True` (activé), aligné avec la spec et le web IHM
- La flag `--no-auto-done` permet une désactivation explicite (meilleur que d'inverser le flag)
- Le backend reçoit déjà `auto_done: bool = True` par défaut (server.py:720), pas de changement backend nécessaire
- Pattern Typer : utiliser deux noms de flag (`--auto-done` / `--no-auto-done`) pour une option booléenne avec défaut `True` rend l'intention claire et l'aide auto-générée plus lisible

**Suivant** : L'option CLI est complète. Passer à la tâche suivante : **Add task selection checkboxes to web IHM**


---
*2026-03-08 10:39* | track: amélioration-gestion-des-tasks

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
*2026-03-08 10:40* | track: amélioration-gestion-des-tasks

**Validation du pattern "Select All":**
- L'ordre de sélection suit l'ordre du plan (pas d'ordre arbitraire)
- `state.bulkSelectedTaskIds = allTasks.map(t => t.id)` garantit que l'ordre est préservé
- Le toggle du bouton utilise `hasBulkSelection = state.bulkSelectedTaskIds.length > 0` (simple et correct)
- Le commentaire du développeur sur "le classement naturel" est respecté ✓

**Prochaine tâche:** Modifier la commande CLI `arche switch` pour supporter les opérations bulk (via `--bulk` flag).


---
*2026-03-08 10:46* | track: amélioration-gestion-des-tasks

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
*2026-03-08 10:49* | track: amélioration-gestion-des-tasks

### Validation de la tâche courante — Implémentation bulk

**Situation trouvée** :
- La tâche "Implement bulk execution logic in backend" (ID: 373f1e02) était marquée `IN_PROGRESS` mais déjà **100% implémentée et commitée** dans le commit `3303e8b`
- Le backend endpoint `POST /api/tracks/{track_id}/tasks/bulk-run` existe avec tous les éléments requis

**Ce qui a été validé** :

1. **Backend bulk endpoint** (`web/server.py:823-939`) ✓
   - Accepte POST request avec `BulkTaskRunRequest` (task_ids, comment, auto_done)
   - Valide l'existence des tâches (404 si manquante)
   - Filtre les DONE automatiquement (400 si tous DONE ou list empty)
   - Exécute chaque tâche en séquence avec subprocess streaming
   - Émet les streaming markers (`__TASK_START__`, `__TASK_DONE__`, `__BULK_DONE__`)
   - Extrait et persiste les architecture notes per-task
   - Auto-marque comme DONE si `req.auto_done: bool = True`

2. **CLI bulk support** (`arche.py:793-857`) ✓
   - Flag `--bulk` avec parsing comma-separated task IDs
   - Résout chaque tâche par index/ID/title substring
   - Skip auto des tâches DONE avec message `⊘ Skipping: Task title`
   - Exécution séquentielle via `call_llm()` avec streaming terminal
   - Auto-mark as DONE après chaque tâche (`complete_task()`)
   - Summary avec count + next pending task

3. **Cohérence CLI vs Web IHM** ✓
   - Auto-done: Identique (défaut True, customizable)
   - Bulk execution: Même pattern (order-preserving, DONE filtering, auto-mark)
   - Session logging: Loggé per-task en CLI (acceptable)
   - Minor note: Phase-locked task validation existe au frontend (checkboxes disabled) mais backend n'a pas de vérification explicite (non-blocking car frontend empêche la sélection)

### Points à retenir pour les prochains tracks

1. **Backend should validate phase-locked tasks** : Ajouter une vérification que les tâches ne sont pas locked avant d'exécuter (actuellement frontend-only)
2. **Session logging pattern** : Décider si un bulk run doit être une seule entrée "session" ou per-task (actuellement per-task)
3. **UI enhancement** : Afficher le nombre de tâches sélectionnées dans l'action bar (nice-to-have)

(aucune note)


---
*2026-03-08 11:00* | track: amélioration-gestion-des-tasks

**(aucune note)** — Toutes les décisions critiques ont été documentées dans les tâches précédentes du track. Le design est stable et validé.


---
*2026-03-08 11:08* | track: affichage-dans-les-sections-spec-task-output

**Comportement final :**
1. **Scroll smooth** : L'utilisateur peut remonter dans Spec/Tasks/Output sans que le polling n'interrompe
2. **Smart auto-scroll en Output** : Pendant une task run, Output scroll en bas automatiquement SAUF si l'utilisateur scroll manuellement
3. **Sidebar toujours à jour** : La sidebar se met à jour même pendant le scroll utilisateur (bon pour voir les changements de statut)
4. **Timeout gracieux** : Après 5 secondes d'inactivité du scroll, le polling reprend normalement

**Points importants pour les prochaines tâches :**
- Le timeout de 5 secondes est configurable
- Les event listeners utilisent `{ passive: true }` pour la performance
- La logique ne s'applique qu'à Output ; Spec et Tasks skippent juste la recréation du DOM pendant le scroll


---
*2026-03-08 11:08* | track: affichage-dans-les-sections-spec-task-output

**Décision de design validée** :
- Le timeout de 5 secondes laisse du temps à l'utilisateur pour lire sans interruption (configurable si nécessaire)
- Les event listeners utilisent `{ passive: true }` pour éviter le blocking du thread principal
- La sidebar se met à jour même pendant le scroll (bon pour voir les changements de statut en temps réel)
- L'auto-scroll en Output est **sélectif** : il continue de fonctionner automatiquement tant que l'utilisateur ne scroll pas manuellement, et reprend après 5 secondes d'inactivité
- La logique ne s'applique qu'à Output pour l'auto-scroll ; Spec et Tasks ne se réactualisent que si l'utilisateur ne scroll pas


---
*2026-03-08 11:19* | track: output

**Découvertes clés** :
- L'output actuel est **complètement en mémoire** (`state.outputText`) et affiché dans un unique `<pre id="output-pre">` dans l'onglet Output
- Le système de **terminaux xterm.js est déjà fonctionnel** avec WebSocket → PTY ; il suffit de l'adapter pour l'output de tâche
- Les **streaming markers** (`__TASK_START__`, `__TASK_DONE__`, `__BULK_DONE__`) existent déjà dans l'API et le frontend (bulk)
- Le **nommage des tabs** est générique ("Term 1", "Term 2") ; il faudra l'adapter pour afficher `-task-{id}`
- **Pas de persistance** : les terminaux, une fois supprimés ou l'onglet fermé, disparaissent — c'est attendu

**Points d'attention pour les tâches suivantes** :
1. **Décision : garder ou refactoriser le flux EventSource/fetch** ? (Actuellement `runTask()` utilise EventSource, `runBulkTasks()` utilise fetch)
2. **Gestion des terminaux** : créer une fonction dédiée `createTaskTerminal(taskId, taskTitle)` pour éviter les conflits de nommage
3. **Auto-scroll** : les terminaux xterm.js ont un scroll natif ; vérifier si la logique `_autoScrollOutput()` (app.js:1854+) est nécessaire
4. **Suppression de l'onglet Output** : une fois l'output redirigé vers les terminaux, on peut envisager de supprimer la section Output de l'IHM web (ou la garder pour backward-compat)


---
*2026-03-08 11:20* | track: output

- **Streaming markers** : Les markers API sont utilisables tel-quel pour identifier les transitions de tâches
- **Nommage des tabs** : Le pattern `-task-{taskId}` permet une identification immédiate de la tâche associée
- **Persistance correcte** : Les terminaux xterm persistent dans `state.terminals` indépendamment de la navigation, contrairement à `state.outputText`
- **Refactorisation minimal** : Adapter `runTask()` et `runBulkTasks()` pour utiliser le même pattern d'ajout de terminal


---
*2026-03-08 11:23* | track: output

**Pattern d'implémentation**:
- Suivit le même pattern que `addTerminal()` pour maintenir la cohérence du code
- Les terminaux de tâche et réguliers partagent le même conteneur `terminal-container`
- Format d'ID explicite `-task-{taskId}` permet une identification immédiate dans le UI

**Intégration sans breaking changes**:
- `removeTerminal()` gère déjà le cas `ws: null` via try/catch
- `selectTerminal()` et `_fitActive()` fonctionnent avec n'importe quel ID
- Les terminaux réguliers (`t1`, `t2`, etc.) continuent de fonctionner sans changement

**Points clés pour la prochaine tâche** ("Redirect task output streaming"):
1. `runTask()` utilise actuellement EventSource (GET) ; `runBulkTasks()` utilise fetch (POST)
2. Adapter les deux fonctions pour appeler `createTaskTerminal()` et rediriger le streaming
3. Les streaming markers (`__TASK_START__`, `__TASK_DONE__`, `__BULK_DONE__`) existent déjà dans l'API
4. L'output pane (`state.outputText`) devient optionnel une fois l'intégration faite


---
*2026-03-08 11:27* | track: output

**Pattern d'intégration du streaming vers les terminaux :**

1. **Streaming markers du backend** :
   - Format : `__TASK_START__ {num}/{total} {title}` — utilisé pour identifier et router l'output vers le bon terminal
   - Parse avec regex : `/^(\d+)\/\d+\s+(.*)$/` — extrait le numéro de tâche (1-based)
   - Conversion en 0-based index pour indexer dans `taskIds` array

2. **Création des terminaux** :
   - Chaque terminal a un ID unique `-task-{taskId}` visible dans les tabs
   - `renderTerminalTabs()` détecte déjà ce préfixe et affiche l'ID complet
   - Les terminaux persistent dans `state.terminals` indépendamment de la navigation entre tracks

3. **Routing du streaming** :
   - `runTask()` : crée un terminal et stream tout l'output EventSource vers `taskTerminal.term.write()`
   - `runBulkTasks()` : mappe `currentTaskIndex` depuis les markers vers `taskIds[index]` pour identifier le bon terminal

4. **Pas de breaking changes** :
   - Les terminaux réguliers (`t1`, `t2`, etc.) continuent à fonctionner via `addTerminal()`
   - Les websockets et la gestion des terminaux ne sont pas affectées
   - `state.outputText` continue d'être accumulé pour backward-compat (non-affiché cependant)

**Points critiques pour les tâches suivantes** :
- La suppression de l'affichage dans la section Output dépendra de la complétude de cette redirection
- Vérifier que la navigation entre tracks ne supprime pas les terminaux de tâche (test manuel)
- Les terminaux xterm.js ont un scroll natif — pas besoin de `_autoScrollOutput()` pour eux

(aucune note supplémentaire)


---
*2026-03-08 11:29* | track: output

**Points importants pour les tâches suivantes** :

1. **Functions stubs conservées** : Les fonctions `renderOutputPane()` et `_appendOutput()` restent volontairement comme stubs pour éviter de briser les anciens chemins (interview Q&A, generation, review) qui les appellent toujours via `_startStream()` et `_startPostStream()`.

2. **Scroll behavior** : Les terminaux xterm.js utilisent le scroll natif du navigateur, donc la logique de détection de scroll utilisateur n'était plus nécessaire pour le DOM `output-pre`.

3. **État `state.outputText`** : Toujours accumulé en mémoire pour backward-compat, mais n'est plus affiché nulle part (l'output pane est vide).

4. **Onglet Output** : Reste accessible pour les cas d'usage de l'interview (Q&A), génération de templates, et actions de review. L'utilisateur peut toujours cliquer sur cet onglet, il affiche simplement les panneaux interview/review sans output à la place.
