# Exemple d'Instruction Personnalisée

Voici un exemple d'instruction personnalisée que vous pouvez ajouter via l'API.

## Exemple : Bonnes pratiques Python

```json
{
  "id": "python-best-practices",
  "name": "Bonnes pratiques Python",
  "description": "Instructions pour écrire du code Python propre et maintenable",
  "category": "languages",
  "tags": ["python", "best-practices", "coding-standards", "PEP 8"],
  "content": "# Bonnes pratiques Python\n\n## Nommage\n- Utilisez des noms de variables descriptifs en minuscules avec des underscores\n- Utilisez des noms de classes en PascalCase\n- Utilisez des noms de fonctions en minuscules avec des underscores\n\n## Structure du code\n- Limitez la longueur des fonctions à 50 lignes maximum\n- Utilisez des docstrings pour toutes les fonctions et classes\n- Suivez la convention PEP 8 pour l'indentation (4 espaces)\n\n## Gestion des erreurs\n- Utilisez des blocs try/except spécifiques\n- Ne capturez pas d'exceptions trop générales (Exception)\n- Utilisez des messages d'erreur descriptifs\n\n## Tests\n- Écrivez des tests unitaires pour chaque fonction\n- Utilisez pytest ou unittest\n- Visez une couverture de code de 80% minimum\n\n## Documentation\n- Ajoutez des docstrings à toutes les fonctions et classes\n- Utilisez des commentaires pour expliquer les parties complexes\n- Mettez à jour la documentation lorsque le code change",
  "source": "user",
  "source_url": null,
  "license": "MIT",
  "is_enabled": true
}
```

## Comment ajouter cette instruction via l'API

```bash
curl -X POST http://localhost:7331/api/instructions/store/add \
  -H "Content-Type: application/json" \
  -d @EXAMPLE_CUSTOM_INSTRUCTION.json
```

## Exemple d'instruction pour Node.js

```json
{
  "id": "nodejs-best-practices",
  "name": "Bonnes pratiques Node.js",
  "description": "Instructions pour développer des applications Node.js robustes",
  "category": "languages",
  "tags": ["nodejs", "javascript", "backend", "best-practices"],
  "content": "# Bonnes pratiques Node.js\n\n## Gestion des modules\n- Utilisez des modules ES6 (import/export) plutôt que CommonJS\n- Évitez les dépendances inutiles\n- Utilisez npm ou yarn pour gérer les dépendances\n\n## Gestion des erreurs\n- Utilisez des blocs try/catch pour les opérations asynchrones\n- Implémentez une gestion centralisée des erreurs\n- Ne laissez pas les erreurs non traitées\n\n## Sécurité\n- Validez toujours les entrées utilisateur\n- Utilisez des variables d'environnement pour les secrets\n- Mettez à jour régulièrement les dépendances\n\n## Performance\n- Utilisez des streams pour les fichiers volumineux\n- Évitez les boucles bloquantes\n- Utilisez des bases de données indexées",
  "source": "user",
  "license": "MIT",
  "is_enabled": true
}
```

## Exemple d'instruction pour le développement frontend

```json
{
  "id": "frontend-best-practices",
  "name": "Bonnes pratiques Frontend",
  "description": "Instructions pour développer des interfaces utilisateur modernes",
  "category": "frontend",
  "tags": ["frontend", "react", "vue", "angular", "best-practices"],
  "content": "# Bonnes pratiques Frontend\n\n## Accessibilité\n- Utilisez des attributs ARIA pour améliorer l'accessibilité\n- Assurez-vous que le contraste des couleurs est suffisant\n- Testez avec un lecteur d'écran\n\n## Performance\n- Minimisez les requêtes réseau\n- Utilisez le lazy loading pour les images\n- Implémentez le code splitting\n\n## Responsive Design\n- Utilisez des media queries pour les différents appareils\n- Testez sur différents tailles d'écran\n- Utilisez des unités relatives (rem, em, %)\n\n## Tests\n- Écrivez des tests pour les composants\n- Utilisez des outils comme Jest ou Cypress\n- Testez les cas d'erreur",
  "source": "user",
  "license": "MIT",
  "is_enabled": true
}
```
