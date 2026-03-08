

---
*2026-03-08 11:19*

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
*2026-03-08 11:20*

- **Streaming markers** : Les markers API sont utilisables tel-quel pour identifier les transitions de tâches
- **Nommage des tabs** : Le pattern `-task-{taskId}` permet une identification immédiate de la tâche associée
- **Persistance correcte** : Les terminaux xterm persistent dans `state.terminals` indépendamment de la navigation, contrairement à `state.outputText`
- **Refactorisation minimal** : Adapter `runTask()` et `runBulkTasks()` pour utiliser le même pattern d'ajout de terminal


---
*2026-03-08 11:23*

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
*2026-03-08 11:27*

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
*2026-03-08 11:29*

**Points importants pour les tâches suivantes** :

1. **Functions stubs conservées** : Les fonctions `renderOutputPane()` et `_appendOutput()` restent volontairement comme stubs pour éviter de briser les anciens chemins (interview Q&A, generation, review) qui les appellent toujours via `_startStream()` et `_startPostStream()`.

2. **Scroll behavior** : Les terminaux xterm.js utilisent le scroll natif du navigateur, donc la logique de détection de scroll utilisateur n'était plus nécessaire pour le DOM `output-pre`.

3. **État `state.outputText`** : Toujours accumulé en mémoire pour backward-compat, mais n'est plus affiché nulle part (l'output pane est vide).

4. **Onglet Output** : Reste accessible pour les cas d'usage de l'interview (Q&A), génération de templates, et actions de review. L'utilisateur peut toujours cliquer sur cet onglet, il affiche simplement les panneaux interview/review sans output à la place.
