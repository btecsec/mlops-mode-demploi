from fastapi import FastAPI

from churn_predictor.predict import predict_churn
from churn_predictor.schemas import CustomerFeatures, PredictionResponse

app = FastAPI(title="Churn Predictor API")


@app.get("/health")
def health():
    """Sonde de vie : répond 200 si le processus tourne, sans toucher au modèle."""
    return {"status": "ok"}


@app.post("/predict", response_model=PredictionResponse)
def predict(features: CustomerFeatures):
    """Reçoit les caractéristiques d'un client, retourne la prédiction de désabonnement."""
    return predict_churn(features.model_dump())
