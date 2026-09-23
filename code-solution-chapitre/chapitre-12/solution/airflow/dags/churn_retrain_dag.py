"""DAG de ré-entraînement hebdomadaire du modèle de churn.

Syntaxe TaskFlow (`@dag` / `@task`) : les dépendances se déduisent des appels
de fonction. `evaluate_and_promote(train_challenger())` suffit à dire « attends
la fin de l'entraînement avant d'évaluer ».

Installation : garder AIRFLOW_HOME côté Linux (SQLite verrouille mal sur
/mnt/c) et pointer le dossier de DAGs sur celui du projet.

    export AIRFLOW_HOME=~/airflow
    export AIRFLOW__CORE__DAGS_FOLDER=$(pwd)/airflow/dags
    airflow standalone

Airflow ne tourne pas nativement sous Windows : l'installation passe, mais le
lancement s'arrête sur `AttributeError: module 'os' has no attribute
'register_at_fork'`. Passer par WSL2 ou l'image Docker officielle.
"""

from datetime import datetime, timedelta

from airflow.decorators import dag, task

from churn_predictor.evaluate import get_champion_accuracy, promote_challenger
from churn_predictor.train import train_and_save


@dag(
    schedule="@weekly",
    start_date=datetime(2026, 1, 1),
    catchup=False,          # ne rattrape pas les exécutions passées manquées
    tags=["churn-predictor"],
)
def churn_retrain_pipeline():

    # retries + retry_delay : le piège du chapitre. Un ré-entraînement qui
    # échoue en silence chaque semaine (panne réseau, disque plein) laisse le
    # champion vieillir sans que personne ne le soupçonne.
    @task(retries=2, retry_delay=timedelta(minutes=5))
    def train_challenger() -> dict:
        """Entraîne un nouveau run MLflow, retourne son identifiant et son accuracy."""
        run_id, accuracy = train_and_save()
        # Un XCom doit être sérialisable en JSON : un str et un float passent,
        # un objet scikit-learn non.
        return {"run_id": run_id, "accuracy": accuracy}

    @task(retries=2, retry_delay=timedelta(minutes=5))
    def evaluate_and_promote(challenger: dict) -> str:
        """Compare au champion actuel, promeut seulement si meilleur."""
        current_accuracy = get_champion_accuracy()
        challenger_accuracy = challenger["accuracy"]
        if challenger_accuracy > current_accuracy:
            # On promeut le run qu'on vient de mesurer, désigné par son
            # identifiant — pas « le dernier arrivé dans le Registry ».
            version = promote_challenger(challenger["run_id"])
            return f"promu (v{version}) : {challenger_accuracy:.3f} > {current_accuracy:.3f}"
        return f"conservé : challenger {challenger_accuracy:.3f} <= actuel {current_accuracy:.3f}"

    evaluate_and_promote(train_challenger())


churn_retrain_pipeline()
