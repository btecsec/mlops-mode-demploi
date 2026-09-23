"""Corrigé des tests du Chapitre 7.

Vérifie qu'une version portant l'alias `champion` existe dans le Registry et
qu'elle se recharge par son alias — pas par un chemin de fichier à retenir.

Prérequis :
    python -m churn_predictor.train --n-estimators 100
    python -m churn_predictor.train --n-estimators 300
    python -m churn_predictor.register

Lancer depuis `chapitre-07/solution/` :  pytest -v
"""

import mlflow
import pytest
from mlflow import MlflowClient

from churn_predictor.config import EXPERIMENT_NAME, MLFLOW_TRACKING_URI, MODEL_NAME

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


@pytest.fixture(scope="module")
def client() -> MlflowClient:
    return MlflowClient()


@pytest.fixture(scope="module")
def champion(client):
    try:
        return client.get_model_version_by_alias(MODEL_NAME, "champion")
    except Exception:  # MlflowException, RestException selon le backend
        pytest.skip("Aucun champion : lancez train.py puis register.py d'abord.")


def test_experience_nommee_explicitement(champion):
    """Le piège du chapitre : sans set_experiment, tout finit dans 'Default'
    et register.py plante bien plus tard sur un AttributeError sur None.

    Dépend de `champion` pour se mettre en skip sur un historique vide : sans
    ça, le test échoue sur un dépôt fraîchement cloné, où `mlflow.db` — généré
    et gitignoré — n'existe pas encore."""
    assert mlflow.get_experiment_by_name(EXPERIMENT_NAME) is not None


def test_un_champion_existe(champion):
    assert int(champion.version) >= 1


def test_le_champion_est_le_run_le_plus_precis(client, champion):
    """register.py trie par accuracy DESC : le champion doit être le meilleur
    run de l'expérience, pas simplement le dernier lancé."""
    experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    runs = client.search_runs([experiment.experiment_id], order_by=["metrics.accuracy DESC"])
    assert champion.run_id == runs[0].info.run_id


def test_le_champion_se_recharge_par_son_alias(champion):
    """La syntaxe @alias : pas de numéro de version à mémoriser, pas de chemin
    de fichier local. C'est ce qui rend le Chapitre 14 (SageMaker) possible."""
    model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}@champion")
    assert model is not None


def test_les_hyperparametres_sont_traces(client, champion):
    """Un run sans param loggé ne répond pas à la question du chapitre :
    « quelle version tourne, avec quels hyperparamètres ? »"""
    run = client.get_run(champion.run_id)
    assert "n_estimators" in run.data.params
    assert 0.5 < run.data.metrics["accuracy"] < 1.0
