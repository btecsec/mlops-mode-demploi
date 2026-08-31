from pathlib import Path

import pandas as pd

# chemin absolu déduit du fichier : le script marche depuis n'importe quel dossier
RACINE = Path(__file__).resolve().parents[1]
CSV = RACINE / "data" / "raw" / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
df = pd.read_csv(CSV)

# 1. correction : les 11 TotalCharges vides deviennent 0.0 (tenure = 0)
df["TotalCharges"] = df["TotalCharges"].replace(" ", "0.0")

# 2. arrivée : deux nouveaux clients du mois, mêmes 21 colonnes
nouveaux = pd.DataFrame([
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
])

# concat puis réécriture : le fichier suivi par DVC change d'octets, donc de hash
df = pd.concat([df, nouveaux], ignore_index=True)
df.to_csv(CSV, index=False)
print(f"{len(df)} lignes écrites")
