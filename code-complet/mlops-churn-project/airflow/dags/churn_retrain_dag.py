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

    @task.branch
    def should_retrain() -> str:
        """Ne déclenche le ré-entraînement (Ch. 11) que si le drift dépasse le seuil.

        Import local : le scheduler relit ce fichier toutes les quelques secondes
        pour découvrir les DAG. Charger Evidently à chaque passage ralentirait ce
        parsing, et une erreur d'import ferait disparaître le DAG de l'interface.
        """
        from monitoring.check_drift import DRIFT_THRESHOLD, check_drift

        return "train_challenger" if check_drift() > DRIFT_THRESHOLD else "skip_retrain"

    @task
    def skip_retrain() -> str:
        """Branche « rien à faire », explicite plutôt que muette : dans
        l'interface on voit que le DAG a tourné et *décidé*, au lieu de se
        demander s'il a planté."""
        return "drift sous le seuil : champion conservé, aucun ré-entraînement"

    decision = should_retrain()
    decision >> evaluate_and_promote(train_challenger())
    decision >> skip_retrain()


churn_retrain_pipeline()
