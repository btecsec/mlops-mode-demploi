from pathlib import Path

# Racine du projet, calculée automatiquement — jamais de chemin en dur.
# parents[2] : config.py -> churn_predictor -> src -> racine du projet.
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT_DIR / "data" / "raw" / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
TARGET_COLUMN = "Churn"

# --- Ajouts du Chapitre 5 ---
MODEL_PATH = ROOT_DIR / "models" / "churn_model.pkl"

# Colonnes catégorielles du dataset : celles que le OneHotEncoder doit traduire
# en colonnes binaires. Un modèle ne sait pas lire "Month-to-month".
CATEGORICAL_COLUMNS = [
    "gender", "Partner", "Dependents", "PhoneService", "MultipleLines",
    "InternetService", "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies", "Contract",
    "PaperlessBilling", "PaymentMethod",
]
# Déjà exploitables telles quelles : elles passent par `remainder="passthrough"`.
NUMERIC_COLUMNS = ["SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"]
