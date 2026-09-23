"""Logique champion / challenger du Chapitre 11.

Le DAG hebdomadaire entraîne un modèle (le *challenger*) et ne remplace celui
qui porte l'alias `champion` que si le challenger est mesurablement meilleur.
Sans cette comparaison, un ré-entraînement automatisé peut dégrader la
production en silence — l'automatisation amplifie les erreurs autant que les
bonnes pratiques.
"""

import mlflow
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException

from churn_predictor.config import MLFLOW_TRACKING_URI, MODEL_NAME

# Même base que train.py et register.py (Ch. 7). Sans cette ligne, le client
# interroge le backend par défaut de MLflow : Registry vide, et l'erreur
# "Registered Model with name=churn-predictor not found" au premier run du DAG.
# Le scheduler Airflow lance chaque tâche depuis son propre répertoire de
# travail, jamais depuis la racine du projet : le piège du Chapitre 7, rejoué.
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


def get_champion_accuracy() -> float:
    """Accuracy du run associé à la version portant l'alias `champion`.

    Retourne 0.0 si aucun champion n'est désigné : au tout premier run du DAG,
    le Registry est vide et le challenger doit gagner par défaut. Lever une
    exception ici bloquerait le pipeline sur son premier passage.
    """
    client = MlflowClient()
    try:
        champion = client.get_model_version_by_alias(MODEL_NAME, "champion")
    except MlflowException as exc:
        # Seul « l'alias n'existe pas » vaut 0.0. Un serveur injoignable ou des
        # droits refusés lèvent la même classe d'exception : les avaler ferait
        # promouvoir un challenger jamais comparé à personne. Une porte de
        # qualité doit fermer quand elle ne sait pas, pas s'ouvrir.
        if exc.error_code != "RESOURCE_DOES_NOT_EXIST":
            raise
        return 0.0
    return client.get_run(champion.run_id).data.metrics["accuracy"]


def promote_challenger(run_id: str) -> str:
    """Enregistre le run gagnant dans le Registry et lui donne l'alias `champion`.

    Le run est passé en paramètre, jamais deviné. Promouvoir « la version la
    plus élevée » déplacerait l'alias sur un modèle qui n'est pas celui que la
    comparaison vient de valider — et comme le DAG n'enregistre rien de
    lui-même, l'alias retomberait sur la version déjà en place : « promu »
    s'afficherait sans que rien ne change.

    Rien n'est supprimé : contrairement aux anciens stages MLflow, il n'existe
    pas de statut `Archived` à gérer. L'ancienne version champion reste
    consultable par son numéro, donc disponible pour un rollback (Ch. 16).
    """
    version = mlflow.register_model(f"runs:/{run_id}/model", MODEL_NAME).version
    MlflowClient().set_registered_model_alias(
        name=MODEL_NAME, alias="champion", version=version,
    )
    return version
