"""Corrigé des tests du Chapitre 5.

TestClient simule des requêtes HTTP sans lancer de vrai serveur ni ouvrir de
port : rapide, reproductible, exécutable en CI (Chapitre 10).

Prérequis : `python -m churn_predictor.train` a produit models/churn_model.pkl.
Lancer depuis `chapitre-05/solution/` :  pytest -v
"""

import pytest
from fastapi.testclient import TestClient

from churn_predictor.app import app
from churn_predictor.config import MODEL_PATH

client = TestClient(app)

PAYLOAD = {
    "gender": "Female", "SeniorCitizen": 0, "Partner": "No", "Dependents": "No",
    "tenure": 2, "PhoneService": "Yes", "MultipleLines": "No",
    "InternetService": "Fiber optic", "OnlineSecurity": "No", "OnlineBackup": "No",
    "DeviceProtection": "No", "TechSupport": "No", "StreamingTV": "No",
    "StreamingMovies": "No", "Contract": "Month-to-month", "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check", "MonthlyCharges": 95.5, "TotalCharges": 191.0,
}

needs_model = pytest.mark.skipif(
    not MODEL_PATH.exists(),
    reason="Modèle absent : lancez `python -m churn_predictor.train` d'abord.",
)


def test_health():
    """/health ne touche pas au modèle : elle doit répondre même sans .pkl."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@needs_model
def test_predict_returns_probability():
    response = client.post("/predict", json=PAYLOAD)
    assert response.status_code == 200
    assert 0.0 <= response.json()["probability"] <= 1.0


@needs_model
def test_predict_is_order_independent():
    """Le réordonnancement par feature_names_in_ dans predict.py rend l'API
    indifférente à l'ordre des clés du JSON — sans lui, le ColumnTransformer
    lève « Feature names must be in the same order as they were in fit »."""
    inverse = dict(reversed(list(PAYLOAD.items())))
    assert client.post("/predict", json=inverse).json() == client.post("/predict", json=PAYLOAD).json()


def test_predict_rejects_incomplete_payload():
    """Les 19 champs sont obligatoires : Pydantic bloque en 422 avant le modèle."""
    incomplet = {k: v for k, v in PAYLOAD.items() if k != "Contract"}
    assert client.post("/predict", json=incomplet).status_code == 422


def test_predict_rejects_unknown_category():
    """Une valeur hors du CSV est refusée à la porte, pas encodée en silence."""
    faute = {**PAYLOAD, "Contract": "Mensuel"}
    assert client.post("/predict", json=faute).status_code == 422
