import os
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

# --- Ajouts du Chapitre 7 ---
# Base SQLite à un chemin absolu, ancré sur ROOT_DIR : depuis MLflow 3, le
# store fichier ("./mlruns") est en maintenance, MLflow bascule sur SQLite par
# défaut. Sans chemin absolu, deux commandes lancées depuis deux dossiers
# différents écrivent dans deux historiques qui ne se voient jamais.
# --- Modifié au Chapitre 12 ---
# La ConfigMap Kubernetes (ou un simple export local) prend le dessus ; à
# défaut, la base SQLite du Chapitre 7 continue de servir sur le poste de
# développement. Sans ce os.getenv, la ConfigMap resterait décorative : la même
# image tournerait avec l'URI figée à la construction.
MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI",
    f"sqlite:///{(ROOT_DIR / 'mlflow.db').as_posix()}",
)

# Alias du modèle servi, surchargeable lui aussi par la ConfigMap. Jamais
# "Production" : les stages MLflow sont l'ancienne API, abandonnée (Ch. 7).
MODEL_ALIAS = os.getenv("MODEL_ALIAS", "champion")

EXPERIMENT_NAME = "churn-prediction"
MODEL_NAME = "churn-predictor"
