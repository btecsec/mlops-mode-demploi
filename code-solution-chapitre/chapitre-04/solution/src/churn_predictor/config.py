from pathlib import Path

# Racine du projet, calculée automatiquement — jamais de chemin en dur.
# parents[2] : config.py -> churn_predictor -> src -> racine du projet.
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT_DIR / "data" / "raw" / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
TARGET_COLUMN = "Churn"
