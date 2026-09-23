"""Rollback du modèle : redéplace l'alias `champion` sur une version antérieure.

Un rollback de modèle n'est jamais qu'un changement de pointeur. Aucune version
n'est supprimée par `set_registered_model_alias` — celle qu'on quitte reste
consultable par son numéro, donc le rollback est lui-même réversible.

Usage :
    python scripts/rollback_model.py --version 4
    python scripts/rollback_model.py --list        # numéros et accuracy dispo

Le pendant côté déploiement (Ch. 12) :
    kubectl rollout history deployment/churn-api
    kubectl rollout undo deployment/churn-api --to-revision=2
"""

import argparse

import mlflow
from mlflow import MlflowClient

from churn_predictor.config import MLFLOW_TRACKING_URI, MODEL_NAME

# Sans set_tracking_uri, le Registry interrogé est vide : le piège du Ch. 7,
# et le pire moment pour le rencontrer est justement un rollback sous pression.
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


def list_versions() -> None:
    client = MlflowClient()
    champion = client.get_model_version_by_alias(MODEL_NAME, "champion")
    for version in sorted(
        client.search_model_versions(f"name='{MODEL_NAME}'"),
        key=lambda v: int(v.version),
    ):
        accuracy = client.get_run(version.run_id).data.metrics.get("accuracy")
        marque = "  <-- champion" if version.version == champion.version else ""
        print(f"v{version.version:<4} accuracy={accuracy:.4f}{marque}")


def rollback(version: str) -> None:
    client = MlflowClient()
    ancienne = client.get_model_version_by_alias(MODEL_NAME, "champion").version
    client.set_registered_model_alias(name=MODEL_NAME, alias="champion", version=version)
    print(f"Alias 'champion' déplacé de v{ancienne} vers v{version}.")
    print(f"Pour annuler ce rollback : --version {ancienne}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="Numéro de version à promouvoir champion.")
    parser.add_argument("--list", action="store_true", help="Lister les versions.")
    args = parser.parse_args()

    if args.list or not args.version:
        list_versions()
    else:
        rollback(args.version)
