"""Enchaîne les trois briques du chapitre : prédiction, explication, jugement.

    python -m churn_predictor.predict_explain_judge

À lancer depuis la racine du projet : `client.json` (Chapitre 10) est lu par
chemin relatif au dossier de travail. Prérequis : `OPENROUTER_API_KEY` dans
l'environnement (Étape 1 du TP) et un modèle entraîné dans `models/`.

La forêt aléatoire garde la décision, le premier LLM l'habille, le second la
contrôle. Aucune des trois briques ne fait le travail d'une autre.
"""

import json

from churn_predictor.explain import explain_prediction
from churn_predictor.judge import judge_explanation
from churn_predictor.predict import predict_churn


def main() -> None:
    with open("client.json", encoding="utf-8") as f:   # le payload du Chapitre 10
        client = json.load(f)

    resultat = predict_churn(client)                   # le RandomForest, inchangé
    explication = explain_prediction(client, resultat["probability"])

    print(explication)
    print("note du juge :", judge_explanation(explication))


if __name__ == "__main__":
    main()
