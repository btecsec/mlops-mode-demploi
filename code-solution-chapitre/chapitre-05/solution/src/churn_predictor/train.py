import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from churn_predictor.config import CATEGORICAL_COLUMNS, MODEL_PATH
from churn_predictor.data import load_raw_data


def train_and_save() -> None:
    df = load_raw_data()
    print(df.head(1))  # sanity check : les bonnes colonnes sont bien là

    # TotalCharges arrive en texte : quelques clients tout neufs ont une
    # valeur vide au lieu de 0. Sans ce nettoyage, l'entraînement plante.
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce").fillna(0)

    # customerID ne prédit rien (identifiant, pas signal) ; Churn est la cible.
    X = df.drop(columns=["customerID", "Churn"])
    y = (df["Churn"] == "Yes").astype(int)
    # random_state fige le tirage : sans lui, deux exécutions donnent deux
    # scores différents, incomparables entre eux.
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # On encode les catégorielles, on laisse passer les numériques telles quelles.
    # handle_unknown="ignore" : une valeur inédite en production ne fait pas tout tomber.
    preprocessor = ColumnTransformer(
        [("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLUMNS)],
        remainder="passthrough",
    )
    # Le Pipeline embarque prétraitement ET modèle dans un seul objet : le .pkl
    # rejouera exactement le même encodage à la prédiction qu'à l'entraînement.
    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("model", RandomForestClassifier(n_estimators=200, random_state=42)),
    ])

    pipeline.fit(X_train, y_train)
    print(f"Accuracy test : {pipeline.score(X_test, y_test):.3f}")

    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)


if __name__ == "__main__":
    train_and_save()
