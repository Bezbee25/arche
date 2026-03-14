# API des Instructions Personnalisées

Cette documentation décrit comment utiliser les endpoints pour gérer les instructions personnalisées dans arche.

## Structure des Instructions

Une instruction est représentée par le modèle suivant :

```python
{
    "id": "string",              # Identifiant unique de l'instruction
    "name": "string",            # Nom affiché de l'instruction
    "description": "string",     # Description de l'instruction
    "category": "general|languages|frontend|backend|tooling",  # Catégorie
    "tags": ["string"],          # Liste de tags pour la recherche
    "content": "string",         # Contenu Markdown de l'instruction
    "source": "builtin|user|external",  # Source de l'instruction
    "source_url": "string",      # URL source (optionnel)
    "license": "string",         # Licence (optionnel)
    "is_enabled": true           # Indique si l'instruction est activée
}
```

## Endpoints

### 1. Lister toutes les instructions

```bash
GET /api/instructions/store/list
```

**Réponse :**
```json
{
    "instructions": [
        {
            "id": "instruction-1",
            "name": "Instruction 1",
            "description": "Description de l'instruction",
            "category": "general",
            "tags": ["tag1", "tag2"],
            "content": "# Contenu...",
            "source": "user",
            "is_enabled": true
        }
    ]
}
```

### 2. Rechercher des instructions

```bash
GET /api/instructions/store/search?q=recherche&category=general&tags=tag1,tag2
```

**Paramètres (optionnels):**
- `q`: Terme de recherche (recherche dans le nom et la description)
- `category`: Catégorie à filtrer
- `tags`: Liste de tags séparés par des virgules

**Réponse :**
```json
{
    "instructions": [...]
}
```

### 3. Récupérer une instruction spécifique

```bash
GET /api/instructions/store/get/{instruction_id}
```

**Réponse :**
```json
{
    "id": "instruction-1",
    "name": "Instruction 1",
    "description": "Description de l'instruction",
    "category": "general",
    "tags": ["tag1", "tag2"],
    "content": "# Contenu...",
    "source": "user",
    "is_enabled": true
}
```

### 4. Ajouter une nouvelle instruction

```bash
POST /api/instructions/store/add
```

**Corps de la requête (JSON):**
```json
{
    "id": "ma-nouvelle-instruction",
    "name": "Ma Nouvelle Instruction",
    "description": "Description de ma nouvelle instruction",
    "category": "general",
    "tags": ["custom", "exemple"],
    "content": "# Ma Nouvelle Instruction\n\nContenu de l'instruction...",
    "source": "user",
    "is_enabled": true
}
```

**Réponse :**
```json
{
    "success": true,
    "id": "ma-nouvelle-instruction"
}
```

### 5. Mettre à jour une instruction existante

```bash
PUT /api/instructions/store/update
```

**Corps de la requête (JSON):**
```json
{
    "id": "ma-nouvelle-instruction",
    "name": "Instruction Mise à Jour",
    "description": "Description mise à jour",
    "category": "general",
    "tags": ["custom", "updated"],
    "content": "# Instruction Mise à Jour\n\nNouveau contenu...",
    "source": "user",
    "is_enabled": true
}
```

**Réponse :**
```json
{
    "success": true,
    "id": "ma-nouvelle-instruction"
}
```

### 6. Supprimer une instruction

```bash
DELETE /api/instructions/store/delete/{instruction_id}
```

**Réponse :**
```json
{
    "success": true
}
```

### 7. Activer/Désactiver une instruction

```bash
POST /api/instructions/store/enable/{instruction_id}?enabled=true
```

**Paramètre :**
- `enabled`: `true` pour activer, `false` pour désactiver

**Réponse :**
```json
{
    "success": true,
    "enabled": true
}
```

## Exemple d'utilisation avec cURL

### Ajouter une instruction
```bash
curl -X POST http://localhost:7331/api/instructions/store/add \
  -H "Content-Type: application/json" \
  -d '{
    "id": "python-best-practices",
    "name": "Bonnes pratiques Python",
    "description": "Instructions pour écrire du code Python propre et maintenable",
    "category": "languages",
    "tags": ["python", "best-practices", "coding-standards"],
    "content": "# Bonnes pratiques Python\n\n1. Utilisez des noms de variables descriptifs\n2. Évitez les fonctions trop longues\n3. Utilisez des docstrings\n4. Suivez PEP 8",
    "source": "user",
    "is_enabled": true
  }'
```

### Lister toutes les instructions
```bash
curl http://localhost:7331/api/instructions/store/list
```

### Rechercher des instructions Python
```bash
curl "http://localhost:7331/api/instructions/store/search?q=python&category=languages"
```

## Stockage

Les instructions personnalisées sont stockées dans le fichier :
- `.arche-storage/instructions/manifest.json`

Ce fichier est au format JSON et contient toutes les instructions avec leurs métadonnées.

## Intégration avec le frontend

Pour intégrer ces endpoints avec le frontend, vous pouvez utiliser les méthodes suivantes :

```javascript
// Exemple avec fetch API
async function addInstruction(instruction) {
  const response = await fetch('/api/instructions/store/add', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(instruction),
  });
  return await response.json();
}

async function listInstructions() {
  const response = await fetch('/api/instructions/store/list');
  return await response.json();
}
```
