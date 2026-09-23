# Exercice — Chapitre 7

**Starter fourni** : l'état exact laissé par `chapitre-06` — API conteneurisée,
modèle entraîné sans aucun tracking.

**Objectif** : tracer chaque entraînement, comparer plusieurs runs, promouvoir
le meilleur dans le Model Registry.

## À faire, sans regarder `solution/`

1. `pip install mlflow`, puis refiger `requirements.txt`.
2. Ajouter `MLFLOW_TRACKING_URI` à `config.py` — en **chemin absolu**, ancré sur
   `ROOT_DIR`. Ajouter `mlflow.db` au `.gitignore`.
3. Modifier `train.py` : `set_tracking_uri`, `set_experiment`, un `start_run`
   autour du `fit`, `log_param`, `log_metric`, `log_model`. La fonction doit
   désormais **retourner** l'accuracy.
4. Ajouter un argument `--n-estimators` en ligne de commande.
5. Lancer au moins deux runs avec des valeurs différentes, les comparer dans
   `mlflow ui`.
6. Écrire `register.py` : meilleur run par `accuracy DESC`, `register_model`,
   alias `champion`.

## Questions

1. Supprimez `mlflow.set_experiment(...)`, relancez un entraînement, puis
   `register.py`. Reproduisez l'`AttributeError` et expliquez pourquoi elle
   apparaît si loin de sa cause.
2. Lancez `train.py` depuis `src/` au lieu de la racine, avec un
   `MLFLOW_TRACKING_URI` **relatif**. Combien de bases `mlflow.db` avez-vous ?
3. Quelle différence concrète entre `joblib.dump` et `mlflow.sklearn.log_model` ?
   Regardez ce que contient le dossier d'artefacts du run.
4. Relancez `register.py` deux fois. Que devient la version 1 ? Pourquoi n'est-elle
   pas supprimée ?
5. Pourquoi un **alias** plutôt qu'un stage `Production` ?

## Bonus

- Boucler sur `[50, 100, 200, 400]` estimateurs et loguer aussi le temps
  d'entraînement (`mlflow.log_metric("fit_seconds", ...)`). Le meilleur modèle
  est-il toujours celui qu'on veut en production ?
- Loguer la matrice de confusion en artefact (`mlflow.log_figure`) — l'accuracy
  seule ment sur des données déséquilibrées (Chapitre 2).

## Critères de réussite

- Deux runs au moins apparaissent dans l'expérience `churn-prediction`.
- `models:/churn-predictor@champion` se recharge sans erreur.
- Le champion est bien le run le plus précis, pas simplement le dernier.
- `pytest` passe au vert.

## Piège de ce chapitre

Un `MLFLOW_TRACKING_URI` relatif ou une expérience non nommée : deux façons de
se retrouver avec un historique éclaté et un Registry vide au pire moment.
