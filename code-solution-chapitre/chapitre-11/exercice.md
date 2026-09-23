# Exercice — Chapitre 11

**Starter fourni** : l'état exact laissé par `chapitre-10` — CI/CD active,
modèle réentraîné à la main quand quelqu'un y pense.

**Objectif** : planifier le ré-entraînement, et ne promouvoir un nouveau modèle
que s'il bat le champion actuel.

## À faire, sans regarder `solution/`

1. Installer Airflow (WSL2 ou Docker si vous êtes sous Windows), garder
   `AIRFLOW_HOME` dans le système de fichiers Linux et pointer
   `AIRFLOW__CORE__DAGS_FOLDER` sur `airflow/dags/` du projet, lancer
   `airflow standalone`.
2. Faire retourner à `train_and_save()` l'identifiant de son run en plus de
   son accuracy.
3. Écrire `src/churn_predictor/evaluate.py` avec deux fonctions :
   `get_champion_accuracy()` et `promote_challenger(run_id)`. Réfléchir au cas
   du tout premier run, quand aucun champion n'existe encore.
4. Écrire `airflow/dags/churn_retrain_dag.py` en syntaxe TaskFlow : une tâche
   qui entraîne, une tâche qui compare et promeut, planifiées `@weekly` avec
   `catchup=False`. Les deux tâches se passent un dictionnaire, pas un nombre.
5. Ajouter une politique de reprise sur chaque tâche.
6. Déclencher le DAG à la main, vérifier l'onglet « Graph » dans l'interface.
7. Ajouter `airflow/*` (sauf `airflow/dags/`) au `.gitignore`.

## Questions

1. Que se passe-t-il au tout premier run, quand le Registry ne contient aucun
   alias `champion` ? Faites-le pour de vrai : supprimez l'alias et relancez.
2. Retirez `catchup=False` et fixez `start_date` à janvier 2024. Combien
   d'exécutions Airflow déclenche-t-il au démarrage du scheduler ?
3. Faites échouer volontairement `train_challenger` (renommez le CSV). La tâche
   `evaluate_and_promote` s'exécute-t-elle quand même ? Avec quel statut
   apparaît-elle dans l'interface ?
4. Entraînez un modèle volontairement mauvais (`--n-estimators 1`),
   enregistrez-le, puis lancez le DAG. Le champion change-t-il ? Pourquoi ?
5. Retirez `mlflow.set_tracking_uri(...)` d'`evaluate.py` et relancez le DAG
   depuis Airflow (pas depuis votre terminal). Quelle erreur obtenez-vous, et
   pourquoi ne se produit-elle pas quand vous appelez la fonction à la main ?
6. Remplacez `promote_challenger(run_id)` par une version qui pose l'alias sur
   la version la plus élevée du Registry, puis lancez le DAG deux fois. Que
   raconte le message de sortie, et que montre le Registry ?
7. Coupez le serveur MLflow et lancez le DAG. `get_champion_accuracy()`
   retourne-t-elle `0.0` ? Que se passerait-il si c'était le cas ?

## Bonus

- Ajouter une troisième tâche `notify` qui poste le résultat de la promotion sur
  un webhook Slack ou Discord. Doit-elle s'exécuter aussi en cas d'échec ?
  (Chercher `trigger_rule`.)
- Ajouter `on_failure_callback` au DAG pour être alerté d'un échec — le vrai
  complément de `retries`.
- Remplacer la comparaison sur l'accuracy par une comparaison sur le rappel
  (*recall*) de la classe `Churn = Yes`. Le champion change-t-il ? Relire la
  baseline métier du Chapitre 3 avant de répondre.
- Déclencher le DAG depuis la CI du Chapitre 10 après un merge sur `main`, au
  lieu d'attendre lundi.

## Critères de réussite

- Le DAG apparaît dans l'interface Airflow, sans erreur d'import.
- Un déclenchement manuel se termine en `success`, les deux tâches vertes.
- Un challenger moins bon que le champion ne le remplace pas.
- Un challenger meilleur redéplace l'alias, et l'ancienne version reste
  consultable par son numéro.
- La version promue est bien celle du run que le DAG vient d'entraîner.
- `pytest` passe au vert, y compris sous Windows sans Airflow installé.

## Piège de ce chapitre

Un DAG sans `retries` ni alerte sur échec. Le pipeline échoue en silence chaque
semaine et le modèle vieillit — l'automatisation a juste rendu le problème plus
discret.
