import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from datetime import datetime, timedelta

from airflow.decorators import dag, task

from churn_predictor.train import train_and_save
from churn_predictor.evaluate import get_champion_accuracy, promote_challenger


@dag(
    schedule="@weekly",
    start_date=datetime(2026, 9, 1),
    catchup=False,       # ne rattrape pas les exécutions passées manquées
    tags=["churn-predictor"],
)
def churn_retrain_pipeline():

    @task(retries=2, retry_delay=timedelta(minutes=5))
    def train_challenger() -> dict:
        """Entraîne un nouveau run MLflow, retourne son identifiant et son accuracy."""
        run_id, accuracy = train_and_save()
        return {"run_id": run_id, "accuracy": accuracy}

    @task
    def evaluate_and_promote(challenger: dict) -> str:
        """Compare au champion actuel, promeut seulement si meilleur."""
        current_accuracy = get_champion_accuracy()
        challenger_accuracy = challenger["accuracy"]
        if challenger_accuracy > current_accuracy:
            # On promeut le run qu'on vient de mesurer, désigné par son
            # identifiant — pas "le dernier arrivé dans le Registry".
            version = promote_challenger(challenger["run_id"])
            return f"promu : version {version}, {challenger_accuracy:.3f} > {current_accuracy:.3f}"
        return f"conservé : challenger {challenger_accuracy:.3f} <= actuel {current_accuracy:.3f}"

    evaluate_and_promote(train_challenger())


churn_retrain_pipeline()
