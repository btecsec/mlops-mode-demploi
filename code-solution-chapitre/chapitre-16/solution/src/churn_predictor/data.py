import pandas as pd

from churn_predictor.config import DATA_PATH, TARGET_COLUMN


def load_raw_data() -> pd.DataFrame:
    """Charge le dataset brut Telco Customer Churn.

    Le chemin vient de config.py, jamais d'une chaîne relative : la fonction
    donne le même résultat qu'on l'appelle depuis la racine, depuis tests/,
    ou depuis un DAG Airflow (Chapitre 11).
    """
    return pd.read_csv(DATA_PATH)


def churn_rate(df: pd.DataFrame) -> float:
    """Retourne la proportion de clients ayant résilié (baseline métier)."""
    return (df[TARGET_COLUMN] == "Yes").mean()
