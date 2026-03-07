

---
*2026-03-07 19:29*

- **Theme key scoping**: La clé localStorage est `arche-theme-<projectName>` où `projectName` vient de `/api/project`. L'early-apply script dans `<head>` itère sur toutes les clés `arche-theme-*` pour trouver la plus récente, ce qui fonctionne bien en pratique (une session browser = un projet).
- **xterm.js theme update**: `term.options.theme = {...}` fonctionne avec xterm.js 5.x pour mettre à jour le thème en live sans recréer le terminal. Les couleurs ANSI du contenu existant ne changent pas (elles sont rendues en bitmap), seul le background/foreground/cursor change immédiatement.
- **Hard-coded colors**: Plusieurs couleurs étaient hard-codées dans le CSS original (`#252525`, `#1a2a1a`, etc.). Elles ont été remplacées par des variables CSS — point d'attention pour toute future couleur ajoutée dans le CSS.
- **Flash prevention**: Le script inline `<head>` couvre le cas où la page charge avec un thème non-Dark. Il relit les palettes dupliquées (légère redondance avec `THEMES` dans app.js) — acceptable car les données sont petites et cette approche évite tout FOUC sans dépendance à l'ordre de chargement des scripts.


---
*2026-03-07 19:38*

- **Cause racine du bug** : les listeners du bouton Theme étaient enregistrés dans `setupTheme()`, qui était appelé **après** un `await api.getProject()` dans `init()`. Si `setupTerminal()` (appelé juste avant le `await`) levait une exception — notamment si xterm.js (CDN) n'était pas encore chargé — l'exception interrompait `init()` et `setupTheme()` n'était jamais atteint. Résultat : `btn-theme` n'avait aucun listener.

- **Pattern à retenir** : les `addEventListener` sur des éléments UI statiques (boutons présents dans le HTML dès le chargement) doivent être enregistrés dans `setupEventListeners()` (synchrone), **pas** dans des fonctions appelées après un `await`. Ne jamais dépendre d'une réponse réseau pour enregistrer des listeners de base.

- **Guard ajouté** : `try/catch` autour de `setupTerminal()` pour isoler les erreurs xterm.js des autres initialisations.


---
*2026-03-07 19:46*

- **Stacking context & flex order** : dans un flex container sans z-index explicite, les éléments sont empilés dans l'ordre DOM. Un élément avec `overflow: hidden` (comme `#main`) crée un stacking context et peut masquer un dropdown `position: absolute` qui dépasse d'un élément frère précédent dans le DOM (`#header`). Toujours donner un `z-index` explicite à un header qui contient des dropdowns.
- **Pattern général** : tout composant header/navbar contenant un dropdown doit avoir `position: relative; z-index: N` pour se garantir d'être au-dessus du contenu principal.
- **Le JS était correct** — le listener du bouton, le toggle de la classe `.hidden`, les `window.applyTheme` / `window.closeThemeDropdown` exposés globalement, tout fonctionnait. Le bug était purement CSS/stacking.
