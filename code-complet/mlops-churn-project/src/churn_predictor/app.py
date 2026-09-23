from fastapi import FastAPI

from churn_predictor.predict import predict_churn
from churn_predictor.schemas import CustomerFeatures, PredictionResponse
from prometheus_fastapi_instrumentator import Instrumentator
import csv
from datetime import datetime, timezone

from churn_predictor.config import PREDICTIONS_LOG


app = FastAPI(title="Churn Predictor API")

Instrumentator().instrument(app).expose(app)  # ajoute GET /metrics


def log_prediction(features: dict, result: dict) -> None:
    """Journalise chaque requête /predict : nécessaire pour comparer
    ensuite les données de production à la baseline d'entraînement."""
    PREDICTIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    is_new = not PREDICTIONS_LOG.exists()
    with open(PREDICTIONS_LOG, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", *features, "probability"])
        if is_new:
            writer.writeheader()
        writer.writerow({"timestamp": datetime.now(timezone.utc).isoformat(), **features, "probability": result["probability"]})

@app.get("/health")
def health():
    """Sonde de vie : répond 200 si le processus tourne, sans toucher au modèle."""
    return {"status": "ok"}


@app.post("/predict", response_model=PredictionResponse)
def predict(features: CustomerFeatures):
    """Reçoit les caractéristiques d'un client, retourne la prédiction de désabonnement."""
    payload = features.model_dump()
    result = predict_churn(payload)
    log_prediction(payload, result)   # la ligne qui alimente la Couche 2
    return result

