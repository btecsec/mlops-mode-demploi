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
    def train_challenger() -> float:
        """Entraîne un nouveau run MLflow, retourne son accuracy."""
        return train_and_save()

    @task
    def evaluate_and_promote(challenger_accuracy: float) -> str:
        """Compare au champion actuel, promeut seulement si meilleur."""
        current_accuracy = get_champion_accuracy()
        if challenger_accuracy > current_accuracy:
            promote_challenger()
            return f"promu : {challenger_accuracy:.3f} > {current_accuracy:.3f}"
        return f"conservé : challenger {challenger_accuracy:.3f} <= actuel {current_accuracy:.3f}"

    evaluate_and_promote(train_challenger())


churn_retrain_pipeline()
