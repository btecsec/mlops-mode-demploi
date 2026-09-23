import csv
from datetime import datetime, timezone

from fastapi import FastAPI, Header
from prometheus_fastapi_instrumentator import Instrumentator

from churn_predictor.audit import log_prediction_audit
from churn_predictor.config import PREDICTIONS_LOG
from churn_predictor.predict import predict_churn
from churn_predictor.schemas import CustomerFeatures, PredictionResponse

app = FastAPI(title="Churn Predictor API", version="0.1.0")

# --- Ajout du Chapitre 15 : Couche 1, la santé technique ---------------------
# Une seule ligne ajoute GET /metrics au format que Prometheus lit nativement :
# latence, nombre de requêtes, codes de retour. Aucune instrumentation manuelle.
Instrumentator().instrument(app).expose(app)


def log_prediction(features: dict, result: dict) -> None:
    """Journalise chaque requête /predict — Couche 2 du monitoring (Ch. 15).

    Ce journal ne contient que des features, jamais d'identité : il sert à
    comparer la production à la baseline d'entraînement, pas à savoir qui a
    appelé. L'audit trail du Chapitre 16 vit dans un fichier séparé.
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
def predict(
    features: CustomerFeatures,
    # L'identité n'est pas une feature : elle vient de l'en-tête, posé par la
    # passerelle ou le service appelant, jamais du corps de la requête. Le
    # modèle n'a donc aucun moyen d'apprendre sur un identifiant client, et le
    # schéma du Chapitre 5 reste inchangé.
    x_customer_id: str = Header(default="anonymous"),
    x_caller: str = Header(default="unknown"),
):
    """Reçoit les caractéristiques d'un client, retourne la prédiction de désabonnement."""
    payload = features.model_dump()
    result = predict_churn(payload)

    log_prediction(payload, result)                              # Ch. 15 : le drift
    log_prediction_audit(x_customer_id, result, x_caller)        # Ch. 16 : l'auditeur
    return result
