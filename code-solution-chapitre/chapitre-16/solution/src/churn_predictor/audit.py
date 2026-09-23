"""Audit trail : qui a demandé quoi, sur quel client, avec quelle version.

Le journal du Chapitre 15 sert au drift : il enregistre des *features*. Celui-ci
sert à un auditeur : il enregistre une *responsabilité*. Deux usages, deux
fichiers — mélanger les deux reviendrait à donner à l'équipe data un accès
permanent aux traces d'accès, et à l'auditeur un fichier illisible.
"""

import csv
from datetime import datetime, timezone
from functools import lru_cache

import mlflow
from mlflow import MlflowClient

from churn_predictor.config import AUDIT_LOG, MLFLOW_TRACKING_URI, MODEL_NAME
from churn_predictor.privacy import pseudonymize

# Même réflexe qu'aux Chapitres 7, 10, 13 et 14 : sans URI explicite, le Registry
# interrogé est vide et la version du modèle reste introuvable.
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

AUDIT_FIELDS = ["timestamp", "caller", "customer_hash", "model_version", "probability"]

# Valeur écrite quand le Registry est injoignable : une ligne d'audit
# incomplète vaut mieux qu'une prédiction non tracée. Perdre la trace est
# irréversible, perdre le numéro de version ne l'est pas.
VERSION_INCONNUE = "unknown"


@lru_cache(maxsize=1)
def get_champion_version() -> str:
    """Version portant l'alias champion, mise en cache au premier appel.

    C'est elle qui rend chaque prédiction traçable jusqu'au run MLflow qui l'a
    produite (Ch. 7). Interroger le Registry à chaque requête coûterait un
    aller-retour réseau par prédiction, alors que la version ne change qu'au
    moment d'une promotion (Ch. 11) — donc au redémarrage du service.
    """
    try:
        return MlflowClient().get_model_version_by_alias(MODEL_NAME, "champion").version
    except Exception:  # MlflowException, RestException selon le backend
        return VERSION_INCONNUE


def log_prediction_audit(customer_id: str, result: dict, caller: str) -> None:
    """Écrit une ligne d'audit.

    Elle répond à elle seule à la question de l'auditeur : qui a demandé quoi,
    sur quel client (pseudonymisé), avec quelle version de modèle, et quand.
    """
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    nouveau = not AUDIT_LOG.exists()
    with open(AUDIT_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=AUDIT_FIELDS)
        if nouveau:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "caller": caller,                            # clé API, service appelant…
            "customer_hash": pseudonymize(customer_id),  # jamais l'identifiant réel
            "model_version": get_champion_version(),     # traçable jusqu'au run MLflow
            "probability": result["probability"],
        })
