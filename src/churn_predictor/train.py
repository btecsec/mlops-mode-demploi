import argparse

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from churn_predictor.config import CATEGORICAL_COLUMNS, MLFLOW_TRACKING_URI, MODEL_PATH
from churn_predictor.data import load_raw_data

# Fige l'emplacement de la base SQLite de tracking sur un chemin absolu :
# sinon MLflow la résout relativement au dossier d'exécution, qui change
# selon d'où la commande est lancée.
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

# Nomme explicitement l'expérience : sans ça, tous les runs (de ce projet
# et de tout autre projet MLflow lancé depuis la même machine) atterrissent
# ensemble dans l'expérience "Default", impossible à trier ensuite.
mlflow.set_experiment("churn-prediction")


def train_and_save(n_estimators: int = 200) -> tuple[str, float]:
    df = load_raw_data()
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce").fillna(0)

    X = df.drop(columns=["customerID", "Churn"])
    y = (df["Churn"] == "Yes").astype(int)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    preprocessor = ColumnTransformer(
        [("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLUMNS)],
        remainder="passthrough",
    )
    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("model", RandomForestClassifier(n_estimators=n_estimators, random_state=42)),
    ])

    with mlflow.start_run(run_name=f"rf-{n_estimators}-estimators") as run:
        pipeline.fit(X_train, y_train)
        accuracy = pipeline.score(X_test, y_test)

        mlflow.log_param("n_estimators", n_estimators)
        mlflow.log_metric("accuracy", accuracy)
        mlflow.sklearn.log_model(pipeline, name="model", input_example=X_test.head(1))

        print(f"Run enregistré — accuracy test : {accuracy:.3f}")

        # L'identifiant du run remonte au DAG (Ch. 11) : c'est lui, et pas
        # "la version la plus récente du Registry", que la promotion cible.
        run_id = run.info.run_id

    # L'API et l'image Docker du chapitre 3 chargent encore ce fichier local :
    # on continue à le produire, en plus du tracking MLflow ci-dessus.
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)

    return run_id, accuracy


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-estimators", type=int, default=200)
    args = parser.parse_args()
    train_and_save(args.n_estimators)