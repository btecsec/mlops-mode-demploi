import csv
from datetime import datetime, timezone

import mlflow
from mlflow import MlflowClient

from churn_predictor.config import AUDIT_LOG, MLFLOW_TRACKING_URI
from churn_predictor.privacy import pseudonymize

# Même réflexe qu'aux Chapitres 7, 11 et 14 : sans URI explicite, le Registry
# interrogé est vide et la version du modèle reste intr..ouvable.
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

AUDIT_FIELDS = ["timestamp", "caller", "customer_hash", "model_version", "probability"]


def get_champion_version() -> str:
    """Version portant l'alias champion : c'est elle qui rend chaque
    prédiction traçable jusqu'au run MLflow qui l'a produite (Ch. 7)."""
    return MlflowClient().get_model_version_by_alias("churn-predictor", "champion").version


def log_prediction_audit(customer_id: str, result: dict, caller: str) -> None:
    """Chaque ligne répond désormais à : qui a demandé quoi, sur quel
    client (pseudonymisé), avec quelle version de modèle, et quand."""
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    is_new = not AUDIT_LOG.exists()
    with open(AUDIT_LOG, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=AUDIT_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "caller": caller,                            # clé API, service appelant...
            "customer_hash": pseudonymize(customer_id),  # jamais l'identifiant réel
            "model_version": get_champion_version(),     # traçable jusqu'au run MLflow
            "probability": result["probability"],
        })
