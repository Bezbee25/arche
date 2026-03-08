# Spec: affichage-dans-les-sections-spec-task-output

## Goal

Déplacer l'affichage de l'output d'exécution de tâche depuis la section des tâches vers la section des terminaux dans l'IHM web, avec un nommage explicite identifiant la tâche en cours.

## Context

Actuellement, lorsqu'une tâche est exécutée, son output est affiché dans la section des tâches de l'IHM web. Ce comportement pose deux problèmes :

1. **Persistance incorrecte** : l'output reste visible dans la section des tâches même lorsque l'utilisateur navigue vers un autre track, ce qui crée une confusion sur le contexte de l'output affiché.
2. **Manque d'identification** : il n'est pas possible de distinguer facilement quel output correspond à quelle tâche, surtout quand plusieurs tâches de plusieurs tracks sont lancées simultanément.

La section des terminaux est l'emplacement naturel pour afficher des outputs de type terminal. L'IHM web est le seul périmètre concerné ; le CLI n'est pas impacté.

## Requirements

1. **Déplacement de l'output vers la section des terminaux**
   - L'output d'exécution d'une tâche doit être affiché dans la section des terminaux, et non plus dans la section des tâches.
   - Lorsque l'utilisateur change de track, les outputs des tâches en cours restent visibles dans la section des terminaux (ils ne disparaissent pas et ne sont pas liés à la vue du track actif).
   - Acceptance criteria :
     - Lancer une tâche depuis le track A, naviguer vers le track B : l'output de la tâche du track A reste accessible dans la section des terminaux.
     - La section des tâches n'affiche plus aucun output d'exécution.

2. **Nommage explicite des terminaux de tâche**
   - Chaque terminal d'output de tâche est nommé selon le format `-task-{id}`, où `{id}` est l'identifiant de la tâche concernée.
   - Ce nommage permet à l'utilisateur d'identifier immédiatement à quelle tâche correspond chaque terminal.
   - Si plusieurs tâches sont lancées en parallèle (depuis un ou plusieurs tracks), chaque tâche dispose de son propre terminal nommé distinctement.
   - Acceptance criteria :
     - Lancer la tâche d'id `abc123` : un terminal nommé `-task-abc123` apparaît dans la section des terminaux.
     - Lancer deux tâches simultanément depuis deux tracks différents : deux terminaux distincts apparaissent, chacun avec le nom correspondant à sa tâche.

## Constraints

- Seule l'IHM web est modifiée (fichiers frontend : `web/static/app.js`, `web/static/index.html`, et éventuellement les styles associés).
- Le CLI et le backend (`web/server.py`) ne doivent pas être modifiés.
- Aucune nouvelle dépendance frontend ne doit être introduite.

## Out of Scope

- Toute modification du CLI ou du backend.
- La persistance des outputs de terminaux entre sessions ou rechargements de page.
- La gestion du cycle de vie des terminaux (fermeture automatique, limite du nombre de terminaux, etc.).
- La modification du comportement d'exécution des tâches (déclenchement, auto-done, streaming, etc.).