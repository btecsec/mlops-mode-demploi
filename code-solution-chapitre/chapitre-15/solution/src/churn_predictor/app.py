import csv
from datetime import datetime, timezone

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from churn_predictor.config import PREDICTIONS_LOG
from churn_predictor.predict import predict_churn
from churn_predictor.schemas import CustomerFeatures, PredictionResponse

app = FastAPI(title="Churn Predictor API", version="0.1.0")

# --- Ajout du Chapitre 15 : Couche 1, la santé technique ---------------------
# Une seule ligne ajoute GET /metrics au format que Prometheus lit nativement :
# latence, nombre de requêtes, codes de retour. Aucune instrumentation manuelle.
Instrumentator().instrument(app).expose(app)


def log_prediction(features: dict, result: dict) -> None:
    """Journalise chaque requête /predict.

    Couche 2 du monitoring : sans historique des données réellement reçues, il
    n'y a rien à comparer à la baseline d'entraînement, et donc aucun moyen de
    voir venir une dérive. Un dashboard vert ne dit que « le service répond »,
    jamais « il répond juste ».
    """
    PREDICTIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    nouveau = not PREDICTIONS_LOG.exists()
    with open(PREDICTIONS_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", *features, "probability"])
        if nouveau:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **features,
            "probability": result["probability"],
        })


@app.get("/health")
def health():
    """Sonde de vie : répond 200 si le processus tourne, sans toucher au modèle.

    Volontairement indépendante du modèle : c'est cette route que les probes
    Kubernetes du Chapitre 12 interrogeront toutes les quelques secondes.
    """
    return {"status": "ok"}


@app.post("/predict", response_model=PredictionResponse)
def predict(features: CustomerFeatures):
    """Reçoit les caractéristiques d'un client, retourne la prédiction de désabonnement."""
    payload = features.model_dump()
    result = predict_churn(payload)
    log_prediction(payload, result)   # la ligne qui alimente la Couche 2
    return result
