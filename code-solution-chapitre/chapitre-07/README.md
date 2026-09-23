# Chapitre 7 — MLflow et tracking d'expériences

Chaque entraînement laisse une trace : paramètres, métrique, modèle. Le
meilleur run entre au Model Registry et reçoit l'alias `champion`.

## Ce que le chapitre ajoute

| Fichier | Rôle |
|----|----|
| `config.py` | + `MLFLOW_TRACKING_URI` (SQLite, chemin **absolu**), `EXPERIMENT_NAME`, `MODEL_NAME` |
| `train.py` | `set_experiment`, `start_run`, `log_param`, `log_metric`, `log_model`, `--n-estimators` |
| `register.py` | cherche le meilleur run, l'enregistre, lui pose l'alias `champion` |
| `.gitignore` | + `mlflow.db`, `mlruns/` — un historique généré n'est pas du code |
| `tests/test_registry.py` | un champion existe, c'est bien le meilleur run, il se recharge par alias |

`train_and_save()` **retourne** désormais son accuracy au lieu de l'afficher :
c'est ce qui permettra au DAG du Chapitre 11 de comparer un challenger au champion.

L'API et l'image Docker continuent de charger `models/churn_model.pkl` — les
brancher sur le Registry est le sujet des Chapitres 10 et 12.

## Lancer la solution

```bash
python ../../bootstrap.py 7
cd solution
pip install -r requirements.txt && pip install -e .

python -m churn_predictor.train --n-estimators 100
python -m churn_predictor.train --n-estimators 300
```

```text
Run enregistré — accuracy test : 0.792
Run enregistré — accuracy test : 0.791
```

Deux runs, deux jeux de paramètres, deux métriques, tous conservés — contrairement
au Chapitre 5 où chaque exécution écrasait silencieusement la précédente. Les
valeurs exactes bougent d'une version de scikit-learn à l'autre : c'est l'écart
entre les runs qui compte, pas la troisième décimale.

## Comparer les runs

```bash
mlflow ui --port 5000      # depuis solution/, là où vit mlflow.db
```

Sur <http://127.0.0.1:5000>, l'expérience `churn-prediction` liste les runs,
triables par la colonne `accuracy`.

## Promouvoir le meilleur

```bash
python -m churn_predictor.register
```

```text
Successfully registered model 'churn-predictor'.
Version 1 de 'churn-predictor' promue avec l'alias 'champion'.
```

Au passage suivant, MLflow crée une version 2 : le Registry empile, il n'écrase jamais.

## Vérifier que le Registry répond

```bash
python -c "import mlflow; from churn_predictor.config import MLFLOW_TRACKING_URI; mlflow.set_tracking_uri(MLFLOW_TRACKING_URI); print(type(mlflow.pyfunc.load_model('models:/churn-predictor@champion')))"
```

```text
<class 'mlflow.pyfunc.PyFuncModel'>
```

## Lancer les tests

```bash
pytest -v      # 21 tests (ch. 1 à 4)
```

## Alias, jamais stage

`set_registered_model_alias(..., alias="champion", ...)` remplace les anciens
stages `Staging`/`Production`, dépréciés. Un alias est un pointeur : le
redéplacer ne supprime rien, l'ancienne version reste disponible pour un
rollback (Chapitre 16).

## Le piège du chapitre

Oublier `mlflow.set_experiment("churn-prediction")`. Les runs s'enregistrent
silencieusement dans `Default`, et l'erreur n'apparaît que bien plus tard,
dans `register.py` :

```text
AttributeError: 'NoneType' object has no attribute 'experiment_id'
```

L'erreur ne pointe pas vers sa cause. Nommer l'expérience dès la première ligne
de code d'entraînement évite tout le détour.

## Si ça ne marche pas

Les pannes rencontrées à ce TP, dans l'ordre où elles se déclarent. Le livre ne les déroule pas : elles vivent ici, à côté du code qui les provoque.

| Symptôme | Cause | Correctif |
|----|----|----|
| `Registered Model with name=churn-predictor not found` | `mlflow.set_tracking_uri` manque : le backend par défaut est interrogé, et il est vide | La ligne en tête de `register.py`, ou dans le script appelant |
| L'interface MLflow est vide | `mlflow ui` a été lancé depuis un autre dossier que la racine | La relancer depuis la racine, où vit `mlflow.db` |
| Les runs apparaissent dans l'expérience `Default` | `mlflow.set_experiment` oublié | C'est le piège classique de ce chapitre |
| `Experiment 'churn-prediction' not found` dans `register.py` | Aucun run n'a encore été enregistré | Lancer l'Étape 4 d'abord |
| `[Errno 10048] address already in use` sur le port 5000 | Une interface MLflow tourne déjà | `mlflow ui --port 5001` |
