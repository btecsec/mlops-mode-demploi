import mlflow
from mlflow import MlflowClient

from churn_predictor.config import MLFLOW_TRACKING_URI

EXPERIMENT_NAME = "churn-prediction"
MODEL_NAME = "churn-predictor"

# Même base que train.py — sinon register.py, lancé depuis un autre dossier,
# interroge un historique MLflow vide et ne trouve jamais l'expérience.
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


def register_best_run() -> None:
    client = MlflowClient()
    experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)

    best_run = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["metrics.accuracy DESC"],
        max_results=1,
    )[0]

    model_uri = f"runs:/{best_run.info.run_id}/model"
    result = mlflow.register_model(model_uri, MODEL_NAME)

    client.set_registered_model_alias(
        name=MODEL_NAME, alias="champion", version=result.version,
    )
    print(f"Version {result.version} de '{MODEL_NAME}' promue avec l'alias 'champion'.")


if __name__ == "__main__":
    register_best_run()
