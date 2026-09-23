from functools import lru_cache

import joblib
import pandas as pd

from churn_predictor.config import MODEL_PATH

DECISION_THRESHOLD = 0.5


@lru_cache
def get_model():
    """Charge le modèle depuis le disque une seule fois, puis le réutilise
    à chaque appel — pas de re-lecture disque à chaque requête.

    joblib.load désérialise du pickle : on ne charge ici QUE le fichier
    produit par notre propre train.py, jamais un .pkl d'origine externe
    (un pickle peut exécuter du code arbitraire à l'ouverture).
    """
    return joblib.load(MODEL_PATH)


def predict_churn(features: dict) -> dict:
    model = get_model()
    # Colonnes remises dans l'ordre vu à l'entraînement : un ColumnTransformer
    # refuse un DataFrame dont les colonnes arrivent dans un ordre différent.
    df = pd.DataFrame([features])[list(model.feature_names_in_)]
    proba = float(model.predict_proba(df)[0][1])
    return {"churn": proba >= DECISION_THRESHOLD, "probability": round(proba, 4)}
