import mlflow
from mlflow import MlflowClient

from churn_predictor.config import EXPERIMENT_NAME, MLFLOW_TRACKING_URI, MODEL_NAME

# Même base que train.py — sinon register.py, lancé depuis un autre dossier,
# interroge un historique MLflow vide et ne trouve jamais l'expérience.
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


def register_best_run() -> str:
    """Enregistre le run le plus précis dans le Registry et lui donne
    l'alias `champion`. Retourne le numéro de version créé."""
    client = MlflowClient()
    experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        raise SystemExit(
            f"Expérience '{EXPERIMENT_NAME}' introuvable — lancez d'abord "
            "`python -m churn_predictor.train`. (C'est le piège du chapitre : "
            "sans set_experiment, les runs partent dans 'Default'.)"
        )

    best_run = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["metrics.accuracy DESC"],
        max_results=1,
    )[0]

    model_uri = f"runs:/{best_run.info.run_id}/model"
    result = mlflow.register_model(model_uri, MODEL_NAME)

    # Alias, pas stage : les stages MLflow ("Production", "Staging") sont
    # l'ancienne API, abandonnée. Un alias se redéplace, ne s'archive pas.
    client.set_registered_model_alias(
        name=MODEL_NAME, alias="champion", version=result.version,
    )
    print(f"Version {result.version} de '{MODEL_NAME}' promue avec l'alias 'champion'.")
    return result.version


if __name__ == "__main__":
    register_best_run()
