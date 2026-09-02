import mlflow
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException

from churn_predictor.config import MLFLOW_TRACKING_URI

MODEL_NAME = "churn-predictor"

# Même base que train.py et register.py (Ch. 7). Sans cette ligne, le client
# interroge le backend par défaut de MLflow : Registry vide, et l'erreur
# "Registered Model with name=churn-predictor not found" au premier run du DAG.
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


def get_champion_accuracy() -> float:
    """Accuracy du run associé à la version portant l'alias 'champion'."""
    client = MlflowClient()
    try:
        champion = client.get_model_version_by_alias(MODEL_NAME, "champion")
    except MlflowException:
        return 0.0  # aucun champion désigné : le premier challenger gagne
    run = client.get_run(champion.run_id)
    return run.data.metrics["accuracy"]


def promote_challenger() -> None:
    """Redéplace l'alias 'champion' sur la version la plus récente."""
    client = MlflowClient()
    latest = max(
        client.search_model_versions(f"name='{MODEL_NAME}'"),
        key=lambda v: int(v.version),
    )
    client.set_registered_model_alias(
        name=MODEL_NAME, alias="champion", version=latest.version,
    )
