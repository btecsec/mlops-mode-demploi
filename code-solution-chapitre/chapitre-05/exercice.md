# Exercice — Chapitre 5

**Starter fourni** : l'état exact laissé par `chapitre-04` — package
`churn_predictor` structuré et testé, sans modèle ni API.

**Objectif** : entraîner le modèle, le charger une seule fois, l'exposer en HTTP.

## À faire, sans regarder `solution/`

1. Installer `fastapi`, `uvicorn[standard]`, `joblib`, `httpx`, puis refiger
   `requirements.txt`.
2. Compléter `config.py` : `MODEL_PATH`, `CATEGORICAL_COLUMNS`, `NUMERIC_COLUMNS`.
3. Écrire `train.py` : nettoyage de `TotalCharges`, split 80/20 à `random_state=42`,
   `ColumnTransformer` + `RandomForestClassifier(n_estimators=200)`, `joblib.dump`.
4. Écrire `predict.py` : `get_model()` mis en cache, `predict_churn(features)`
   qui renvoie `{"churn": bool, "probability": float}`.
5. Écrire `schemas.py` (19 champs) et `app.py` (`/health`, `/predict`).
6. Vérifier à la main via Swagger, puis écrire `tests/test_app.py`.

## Questions

1. Pourquoi `customerID` est-il retiré de `X` ? Que se passerait-il si on le gardait ?
2. Que renvoie `pd.to_numeric(" ", errors="coerce")` ? Enlevez la ligne de
   nettoyage de `TotalCharges` et lisez l'erreur de `fit()` en entier.
3. Remplacez `@lru_cache` par un `joblib.load()` à l'intérieur de la route.
   Mesurez la différence sur 50 requêtes successives (`time` ou `hey`).
4. Enlevez la réindexation `[list(model.feature_names_in_)]` dans `predict.py`,
   puis envoyez le payload avec les clés dans l'ordre inverse. Quelle erreur ?
5. Pourquoi `/health` ne doit-elle surtout pas charger le modèle ?

## Bonus

- Rendre le seuil de décision (`0.5`) configurable par variable d'environnement.
  Sur un problème de churn, viser 0,35 augmente le recall — au prix de fausses
  alertes. Justifiez un choix.
- Ajouter une route `POST /predict/batch` qui accepte une liste de clients.

## Critères de réussite

- `python -m churn_predictor.train` affiche une accuracy ≈ 0,79.
- `POST /predict` avec le payload d'exemple renvoie `probability = 0.735`.
- `pytest` passe au vert, sans serveur lancé.
- Un payload à qui il manque un champ renvoie `422`, pas `500`.

## Piège de ce chapitre

Charger le modèle *dans* la fonction de route. Ça marche à une requête, ça
s'écroule à mille. Le modèle ne change pas entre deux appels : il se charge
une fois, au démarrage.
