"""Simule le nouvel export mensuel du service client.

Deux choses changent dans un export réel : des valeurs erronées sont corrigées,
et de nouveaux clients arrivent. Le fichier suivi par DVC change donc d'octets,
donc de hash — c'est exactement ce que le Chapitre 8 veut rendre traçable.

Usage :
    python scripts/simulate_new_export.py     # depuis solution/
"""

from pathlib import Path

import pandas as pd

# Chemin ancré sur le fichier, pas sur le dossier courant : le script reste
# lançable depuis n'importe où (même piège que le MLFLOW_TRACKING_URI du Ch. 7).
CSV = Path(__file__).resolve().parents[1] / "data" / "raw" / "WA_Fn-UseC_-Telco-Customer-Churn.csv"

NOUVEAUX_CLIENTS = [
    {
        "customerID": "9999-NEWAA", "gender": "Female", "SeniorCitizen": 0,
        "Partner": "Yes", "Dependents": "No", "tenure": 2,
        "PhoneService": "Yes", "MultipleLines": "No",
        "InternetService": "Fiber optic", "OnlineSecurity": "No",
        "OnlineBackup": "Yes", "DeviceProtection": "No", "TechSupport": "No",
        "StreamingTV": "Yes", "StreamingMovies": "Yes",
        "Contract": "Month-to-month", "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": 89.10, "TotalCharges": "178.20", "Churn": "Yes",
    },
    {
        "customerID": "9999-NEWBB", "gender": "Male", "SeniorCitizen": 1,
        "Partner": "No", "Dependents": "No", "tenure": 5,
        "PhoneService": "Yes", "MultipleLines": "Yes",
        "InternetService": "DSL", "OnlineSecurity": "Yes",
        "OnlineBackup": "No", "DeviceProtection": "Yes", "TechSupport": "Yes",
        "StreamingTV": "No", "StreamingMovies": "No",
        "Contract": "Two year", "PaperlessBilling": "No",
        "PaymentMethod": "Mailed check",
        "MonthlyCharges": 61.35, "TotalCharges": "306.75", "Churn": "No",
    },
]


def main() -> None:
    df = pd.read_csv(CSV)

    # 1. correction : les 11 TotalCharges vides deviennent 0.0 (clients à tenure = 0)
    df["TotalCharges"] = df["TotalCharges"].replace(" ", "0.0")

    # 2. arrivée : deux nouveaux clients du mois, mêmes 21 colonnes
    df = pd.concat([df, pd.DataFrame(NOUVEAUX_CLIENTS)], ignore_index=True)

    df.to_csv(CSV, index=False)
    print(f"{len(df)} lignes écrites")


if __name__ == "__main__":
    main()
