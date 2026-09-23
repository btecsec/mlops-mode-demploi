# Chapitre 5 — Construire une API de modèle (FastAPI)

Le modèle sort du notebook et devient un service HTTP interrogeable par
n'importe quelle application.

## Ce que le chapitre ajoute

| Fichier | Rôle |
|----|----|
| `config.py` | + `MODEL_PATH`, `CATEGORICAL_COLUMNS`, `NUMERIC_COLUMNS` |
| `train.py` | pipeline scikit-learn complet (OneHot + RandomForest) sérialisé en `.pkl` |
| `predict.py` | chargement du modèle **une seule fois** (`@lru_cache`) + décision métier |
| `schemas.py` | validation Pydantic des 19 colonnes, valeurs autorisées comprises |
| `app.py` | API FastAPI : `GET /health`, `POST /predict` |
| `tests/test_app.py` | `TestClient`, sans serveur ni port ouvert |

## Lancer la solution

```bash
python ../../bootstrap.py 5
cd solution
python -m venv venv && source venv/Scripts/activate
pip install -r requirements.txt && pip install -e .

python -m churn_predictor.train
uvicorn churn_predictor.app:app --reload
```

```text
Accuracy test : 0.791
```

79,1 % contre 73,5 % de baseline naïve (Ch. 3) : le modèle apprend réellement
quelque chose, mais la marge reste modeste — on n'a pas fini d'itérer.

## Interroger l'API

*Terminal PowerShell — dans un second shell*

```powershell
$body = Get-Content ../tests/payload_exemple.json -Raw
Invoke-RestMethod -Uri "http://127.0.0.1:8000/predict" -Method Post -ContentType "application/json" -Body $body
```

```json
{"churn": true, "probability": 0.735}
```

Un client tout neuf (`tenure: 2`), en contrat mensuel, sur fibre : le profil à
risque repéré dès l'exploration du Chapitre 3. `0.735 >= 0.5`, donc `churn: true`.

Swagger UI est servi sans une ligne de code sur <http://127.0.0.1:8000/docs>.

## Lancer les tests

```bash
pytest -v
```

Sept tests : `/health`, forme de la réponse, indifférence à l'ordre des clés,
rejet d'un payload incomplet, rejet d'une catégorie inconnue, plus les deux
tests de données hérités du Chapitre 4.

## Les deux détails qui font tout

- **`@lru_cache` sur `get_model()`** — le modèle est chargé une fois, pas à
  chaque requête. C'est le piège du chapitre : recharger le `.pkl` dans la
  fonction de route marche en test manuel et sature le disque en production.
- **Réindexation par `model.feature_names_in_`** — Pydantic restitue les champs
  dans l'ordre de `schemas.py`, pas celui du CSV. Un `ColumnTransformer` refuse
  tout ordre différent de celui vu au `fit`. Une ligne règle le problème.

## Si ça ne marche pas

Les pannes rencontrées à ce TP, dans l'ordre où elles se déclarent. Le livre ne les déroule pas : elles vivent ici, à côté du code qui les provoque.

| Symptôme | Cause | Correctif |
|----|----|----|
| `FileNotFoundError` sur `models/churn_model.pkl` | Le modèle n'a jamais été entraîné dans ce projet | `python -m churn_predictor.train` (Étape 3) |
| `500 Internal Server Error` sur `/predict` | Payload incomplet : `ValueError: columns are missing` côté serveur | Envoyer les 19 champs, tous obligatoires |
| *Feature names must be in the same order as they were in fit* | Le `DataFrame` est construit sans réindexation | La ligne `[list(model.feature_names_in_)]` de l'Étape 4 |
| Sous PowerShell, `curl` refuse `-H` | `curl` y est un alias d'`Invoke-WebRequest` | `curl.exe`, ou la cmdlet native ci-dessus |
| `[Errno 10048] address already in use` | Un `uvicorn` tourne déjà sur le port 8000 | Le fermer, ou `uvicorn ... --port 8001` |
