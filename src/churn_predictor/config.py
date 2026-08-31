from pathlib import Path

# Racine du projet, calculée automatiquement — jamais de chemin en dur
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT_DIR / "data" / "raw" / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
TARGET_COLUMN = "Churn"

# --- Ajouts par rapport au chapitre 1 ---
MODEL_PATH = ROOT_DIR / "models" / "churn_model.pkl"

# --- Ajouts par rapport au chapitre 3 ---
# Base SQLite à un chemin absolu, ancré sur ROOT_DIR. Deux raisons :
# - depuis MLflow 3, le store fichier ("./mlruns") est en maintenance et
#   MLflow bascule sur SQLite par défaut ;
# - un chemin relatif ("sqlite:///mlflow.db") se résout par rapport au
#   dossier depuis lequel la commande est lancée : deux exécutions depuis
#   deux dossiers différents (racine du projet, puis src/, par exemple)
#   écrivent alors dans deux bases distinctes — train.py et register.py
#   ne se voient plus.
MLFLOW_TRACKING_URI = f"sqlite:///{(ROOT_DIR / 'mlflow.db').as_posix()}"

# Colonnes catégorielles du dataset
CATEGORICAL_COLUMNS = [
    "gender", "Partner", "Dependents", "PhoneService", "MultipleLines",
    "InternetService", "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies", "Contract",
    "PaperlessBilling", "PaymentMethod",
]
NUMERIC_COLUMNS = ["SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"]
