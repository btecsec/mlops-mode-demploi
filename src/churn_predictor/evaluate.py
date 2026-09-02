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
    except MlflowException as exc:
        # Seul "l'alias n'existe pas" vaut 0.0. Un serveur injoignable ou des
        # droits refusés lèvent aussi MlflowException : les avaler ferait
        # promouvoir n'importe quel challenger sur une simple panne réseau.
        if exc.error_code != "RESOURCE_DOES_NOT_EXIST":
            raise
        return 0.0  # aucun champion désigné : le premier challenger gagne
    run = client.get_run(champion.run_id)
    return run.data.metrics["accuracy"]


def promote_challenger(run_id: str) -> str:
    """Enregistre le run gagnant dans le Registry et lui donne l'alias 'champion'."""
    # Le run est passé en paramètre, jamais deviné : promouvoir "la version la
    # plus élevée" déplacerait l'alias sur un modèle qui n'est pas celui que la
    # comparaison vient de valider.
    version = mlflow.register_model(f"runs:/{run_id}/model", MODEL_NAME).version
    MlflowClient().set_registered_model_alias(
        name=MODEL_NAME, alias="champion", version=version,
    )
    return version
