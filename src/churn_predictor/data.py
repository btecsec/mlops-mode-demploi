import pandas as pd
from churn_predictor.config import DATA_PATH


def load_raw_data() -> pd.DataFrame:
    """Charge le dataset brut Telco Customer Churn."""
    return pd.read_csv(DATA_PATH)


def churn_rate(df: pd.DataFrame) -> float:
    """Retourne la proportion de clients ayant résilié (baseline métier)."""
    return (df["Churn"] == "Yes").mean()
