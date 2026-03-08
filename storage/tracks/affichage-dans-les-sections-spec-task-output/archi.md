# Architecture: Affichage dans les sections (spec, task, output)

## Problème identifié

L'auto-refresh toutes les 3 secondes (`refresh()` appelée par `setInterval(refresh, 3000)`) recrée complètement le DOM des onglets spec, tasks, et output. Cela provoquait deux comportements indésirables :

1. **Scroll en Output** : Après `pre.scrollTop = pre.scrollHeight`, le scroll était forcément repoussé en bas toutes les 3 secondes, même si l'utilisateur remontait manuellement.
2. **Blocage du refresh** : Quand l'utilisateur remontait manuellement, le `renderTabContent()` repoussait forcément en bas au bout de quelques secondes, remettant le scroll à zéro.

## Solution implémentée

### 1. Détection du scroll utilisateur

Ajout d'une détection du scroll pour les 3 sections scrollables :
- `tab-spec` (onglet Spec)
- `tasks-scroll` (scrollable dans onglet Tasks)
- `output-pre` (section Output avec le contenu)

**Mécanisme** :
- `setupScrollDetection()` enregistre des listeners `passive: true` sur ces éléments
- Quand l'utilisateur scroll, `state._autoRefreshBlocked = true` et `state._userScrolling = <tab-id>`
- Un timeout de 5 secondes réinitialise ce flag après que l'utilisateur arrête de scroller
- Cela donne 5 secondes à l'utilisateur pour lire du contenu sans être interrompu

### 2. Blocage du polling quand l'utilisateur scroll

Modification de la fonction `refresh()` :
```javascript
// Skip panel re-render if user is scrolling
if (state._autoRefreshBlocked) return;
```

Cette ligne empêche le re-rendu du panel complet si l'utilisateur scroll. La sidebar se met à jour même pendant le scroll (c'est important pour voir les changements de statut).

### 3. Auto-scroll sélectif en Output

Création d'une fonction helper `_autoScrollOutput()` :
```javascript
function _autoScrollOutput() {
  const pre = $id('output-pre');
  if (!pre) return;
  // Only auto-scroll if user is not manually scrolling this element
  if (state._userScrolling !== 'output-pre') {
    pre.scrollTop = pre.scrollHeight;
  }
}
```

Cette fonction est appelée à la place de `pre.scrollTop = pre.scrollHeight` partout dans le code :
- Dans `renderOutputPane()` (ligne 1084)
- Dans les handlers de streaming SSE/fetch (5 emplacements)

## État des variables d'état

Deux nouvelles variables ont été ajoutées au `state` global :
```javascript
state._userScrolling: null,        // id du tab où l'utilisateur scroll
state._autoRefreshBlocked: false,  // true si l'utilisateur scroll quelque part
```

## Points d'attention pour les prochaines tâches

1. **Timeout de blocage** : Actuellement fixé à 5 secondes. Peut être ajusté selon les retours utilisateurs.
2. **Polling en dehors d'Output** : Le polling continue partout mais le panel ne se recrée que si l'utilisateur n'est pas en train de scroller. C'est un bon équilibre entre responsivité et stabilité.
3. **Streaming en Output** : Les handlers de streaming continuent de mettre à jour le contenu en temps réel (c'est voulu), mais seulement auto-scroll si l'utilisateur n'a pas manuellement scrollé.

## Fichiers modifiés

- `web/static/app.js` : Ajout de détection de scroll, blocage du polling, auto-scroll sélectif


---
*2026-03-08 11:08*

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
*2026-03-08 11:08*

**Décision de design validée** :
- Le timeout de 5 secondes laisse du temps à l'utilisateur pour lire sans interruption (configurable si nécessaire)
- Les event listeners utilisent `{ passive: true }` pour éviter le blocking du thread principal
- La sidebar se met à jour même pendant le scroll (bon pour voir les changements de statut en temps réel)
- L'auto-scroll en Output est **sélectif** : il continue de fonctionner automatiquement tant que l'utilisateur ne scroll pas manuellement, et reprend après 5 secondes d'inactivité
- La logique ne s'applique qu'à Output pour l'auto-scroll ; Spec et Tasks ne se réactualisent que si l'utilisateur ne scroll pas
