# Chapitre 11 — Orchestration : ré-entraîner sans y penser

Le ré-entraînement quitte le « quand quelqu'un y pense » pour un DAG Airflow
hebdomadaire. Et le nouveau modèle ne remplace l'ancien que s'il est
mesurablement meilleur.

## Ce que le chapitre ajoute

| Fichier | Rôle |
|----|----|
| `src/churn_predictor/train.py` | Rend `(run_id, accuracy)` : de quoi décider *et* promouvoir |
| `src/churn_predictor/evaluate.py` | `get_champion_accuracy()` et `promote_challenger(run_id)` |
| `airflow/dags/churn_retrain_dag.py` | DAG `@weekly`, deux tâches TaskFlow, `retries=2` |
| `requirements-airflow.txt` | Airflow isolé du `requirements.txt` principal |
| `.gitignore` | `airflow/*` sauf `airflow/dags/` — le runtime n'est pas du code |
| `.dockerignore` | + `airflow/` — l'orchestrateur ne tourne pas dans l'image de l'API |
| `tests/test_evaluate.py` | Cas limites du champion/challenger + lecture AST du DAG |

`train_and_save()` retournait son accuracy depuis le Chapitre 7. Elle retourne
maintenant aussi l'identifiant de son run : comparer deux nombres ne suffit pas,
encore faut-il savoir quel modèle promouvoir ensuite.

## Le DAG en un coup d'œil

```text
@weekly
   │
   ▼
[train_challenger]  ──▶ train_and_save() ──▶ {run_id, accuracy}
   │
   │ TaskFlow : evaluate_and_promote(train_challenger())
   ▼
[evaluate_and_promote]
   │
   ├─ challenger > champion ?  ──▶ register_model(runs:/<run_id>/model)
   │                               puis alias champion sur cette version
   └─ sinon                    ──▶ on garde le champion actuel
```

## Airflow ne tourne pas sous Windows

Airflow ne supporte que les systèmes POSIX. Sous Windows,
`pip install apache-airflow` réussit pourtant sans broncher — c'est au premier
lancement que ça casse :

```text
AttributeError: module 'os' has no attribute 'register_at_fork'
```

`os.register_at_fork` n'existe que là où `fork()` existe. La voie du chapitre est
WSL2 : `wsl --install -d Ubuntu` dans un PowerShell administrateur.

Le `docker-compose.yaml` publié par Airflow est une alternative séduisante, mais
pas un remplacement direct : il ne monte que `dags/`, `logs/`, `plugins/` et
`config/`, jamais `src/`. Le projet n'est donc pas installé dans les containers
et le DAG s'arrête sur `ModuleNotFoundError: No module named 'churn_predictor'`.
Le faire marcher demande une image dérivée qui installe le projet.

C'est pour cette raison qu'Airflow vit dans `requirements-airflow.txt` et non
dans `requirements.txt` : les tests des chapitres 4 à 10 doivent rester
installables et exécutables partout.

## Lancer la solution

L'ordre est celui du TP refondu : tout installer, puis tout lancer.

```bash
python ../../bootstrap.py 10
cd solution
pip install -r requirements.txt && pip install -e .
python -m churn_predictor.train
python -m churn_predictor.register      # crée le premier champion

pytest -v      # 46 tests (ch. 1 à 11)
```

Puis, dans WSL2 ou Docker :

```bash
python3 -m venv .venv-airflow && source .venv-airflow/bin/activate
pip install -r requirements-airflow.txt \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.3.1/constraints-$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")').txt"

export AIRFLOW_HOME=~/airflow                          # jamais sur /mnt/c : SQLite y verrouille mal
export AIRFLOW__CORE__DAGS_FOLDER=$(pwd)/airflow/dags  # les DAGs restent versionnés dans le projet
airflow standalone
```

Si le mot de passe admin ne s'affiche pas, il est dans
`$AIRFLOW_HOME/simple_auth_manager_passwords.json.generated`.

```text
standalone | Airflow is ready
standalone | Login with username: admin  password: <généré>
```

L'interface répond sur <http://localhost:8080>. Déclencher le DAG à la main
plutôt qu'attendre lundi — dans le shell où `AIRFLOW_HOME` a été exporté, jamais
depuis un venv Windows :

```bash
airflow dags trigger churn_retrain_pipeline
airflow dags list-runs churn_retrain_pipeline   # `-d` n'existe plus depuis Airflow 3
```

```text
dag_id                   | run_id                       | state
churn_retrain_pipeline   | manual__2026-08-28T10:03:00Z | success
```

## Tester un DAG sans Airflow

Les quatre derniers tests lisent `churn_retrain_dag.py` en AST au lieu de
l'importer. Un test qui ne tourne que sur les machines Linux ne protège que la
moitié de l'équipe — et sûrement pas la CI d'un lecteur sous Windows. Ce qu'on
vérifie là (planification, `catchup`, `retries`, dépendance entre tâches) est de
toute façon lisible dans la syntaxe.

Les cinq premiers tests, eux, bouchonnent `MlflowClient` : ce qui est vérifié
ici, c'est une décision métier, pas le comportement de MLflow.

## On promeut le modèle qu'on a mesuré, pas « le dernier »

`promote_challenger(run_id)` enregistre le run gagnant dans le Registry, puis
pose l'alias sur la version qui en sort. Chercher « la version la plus élevée »
à la place déciderait sur un modèle et en déploierait un autre — et comme le
DAG n'enregistre rien de lui-même, l'alias retomberait sur la version déjà en
place. Le pipeline afficherait « promu » sans que rien ne change.

Même exigence côté lecture. `get_champion_accuracy()` ne retourne `0.0` que sur
`RESOURCE_DOES_NOT_EXIST`, le code d'erreur de l'alias absent. Un serveur
injoignable ou des droits refusés lèvent la même classe d'exception : les avaler
ferait promouvoir un challenger que personne n'a comparé à personne. Une porte
de qualité doit **fermer** quand elle ne sait pas, pas s'ouvrir.
`test_une_panne_mlflow_ne_vaut_pas_zero` couvre ce cas.

## Le piège du chapitre

Un DAG sans `retries` ni alerte. Le ré-entraînement échoue chaque semaine —
panne réseau vers MLflow, disque plein, dataset corrompu — et personne ne le
voit : le champion vieillit tranquillement, exactement le problème que ce
chapitre devait résoudre.

```python
@task(retries=2, retry_delay=timedelta(minutes=5))
```

Un pipeline automatisé qui échoue en silence n'est pas mieux qu'un humain qui
oublie. Il est juste plus difficile à soupçonner.

## Le piège du répertoire de travail

Le scheduler Airflow lance chaque tâche depuis son propre dossier, jamais
depuis la racine du projet. Sans `mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)`
en tête d'`evaluate.py`, le client interroge le backend par défaut de MLflow :
Registry vide, et `Registered Model with name=churn-predictor not found` au
premier run. C'est le piège du Chapitre 7, rejoué dans un autre décor.

## Si ça ne marche pas

Les pannes rencontrées à ce TP, dans l'ordre où elles se déclarent. Le livre ne les déroule pas : elles vivent ici, à côté du code qui les provoque.

| Symptôme | Cause | Correctif |
|----|----|----|
| `AttributeError: module 'os' has no attribute 'register_at_fork'` | La commande a été tapée dans PowerShell ou CMD, pas dans le terminal Ubuntu | Reprendre dans le terminal Ubuntu de l'Étape 1, venv `.venv-airflow` activé |
| `ModuleNotFoundError: No module named 'churn_predictor'` | Le paquet n'est pas installé dans ce venv, ou `pyproject.toml` n'a pas ses deux blocs `setuptools` | `pip install -e .` dans `.venv-airflow` ; voir le repli ci-dessous |
| Le DAG n'apparaît pas dans l'interface | Erreur d'import silencieuse | `airflow dags list-import-errors` |
| Le run reste en `queued` indéfiniment | Le scheduler ne tourne pas | Laisser `airflow standalone` ouvert dans son terminal |
| `unrecognized arguments: -d` | `list-runs` attend le `dag_id` en positionnel depuis Airflow 3 | Retirer le `-d` de la 2.x |
| `database is locked` | `AIRFLOW_HOME` pointe sous `/mnt/c/` | L'exporter vers `~/airflow`, côté Linux |
| `Registered Model with name=churn-predictor not found` | Le client interroge le backend MLflow par défaut | Vérifier `mlflow.set_tracking_uri` en tête d'`evaluate.py` |
