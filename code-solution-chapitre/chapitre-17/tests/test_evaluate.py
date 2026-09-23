"""Corrigé des tests du Chapitre 11.

Deux familles de tests, pour deux raisons différentes :

1. `evaluate.py` — la logique champion/challenger, testée sur ses cas limites
   avec un Registry MLflow bouchonné. Pas de serveur, pas de base : ce qu'on
   vérifie ici, c'est une décision métier, pas MLflow.
2. `churn_retrain_dag.py` — lu en AST, sans l'importer. Airflow ne s'installe
   pas sous Windows, et un test qui ne tourne que sur la moitié des machines
   ne protège personne. L'analyse syntaxique, elle, tourne partout.

Lancer depuis `chapitre-11/solution/` :  pytest -v
"""

import ast
from pathlib import Path

import pytest
from mlflow.exceptions import MlflowException
from mlflow.protos.databricks_pb2 import INTERNAL_ERROR, RESOURCE_DOES_NOT_EXIST

from churn_predictor import evaluate

DAG_FILE = (
    Path(__file__).resolve().parents[1] / "solution" / "airflow" / "dags" / "churn_retrain_dag.py"
)


# --- Bouchons : le strict minimum de l'API MlflowClient utilisée ---------------

class FakeRun:
    def __init__(self, accuracy):
        self.data = type("Data", (), {"metrics": {"accuracy": accuracy}})()


class FakeVersion:
    def __init__(self, version, run_id="run"):
        self.version = str(version)
        self.run_id = run_id


class FakeClient:
    """Registry en mémoire. `alias=None` simule un Registry sans champion
    désigné ; `erreur` choisit le code d'erreur que MLflow renverrait alors —
    RESOURCE_DOES_NOT_EXIST pour un alias absent, autre chose pour une vraie
    panne."""

    def __init__(self, versions=None, alias=None, accuracy=0.0, erreur=None):
        self.versions = versions or []
        self.alias = alias
        self.accuracy = accuracy
        self.erreur = RESOURCE_DOES_NOT_EXIST if alias is None and erreur is None else erreur
        self.promue = None

    def get_model_version_by_alias(self, name, alias):
        if self.erreur is not None:
            raise MlflowException(
                f"Alias {alias} not found for model {name}", error_code=self.erreur,
            )
        return self.alias

    def get_run(self, run_id):
        return FakeRun(self.accuracy)

    def search_model_versions(self, filter_string):
        return self.versions

    def set_registered_model_alias(self, name, alias, version):
        self.promue = version


@pytest.fixture
def registry(monkeypatch):
    """Injecte un FakeClient à la place de MlflowClient dans evaluate.py."""

    def _make(**kwargs):
        client = FakeClient(**kwargs)
        monkeypatch.setattr(evaluate, "MlflowClient", lambda *a, **kw: client)
        return client

    return _make


# --- get_champion_accuracy ----------------------------------------------------

def test_aucun_champion_donne_zero(registry):
    """Premier run du DAG : le Registry n'a pas d'alias champion. Retourner 0.0
    plutôt que lever garantit que le premier challenger sera promu."""
    registry(alias=None)
    assert evaluate.get_champion_accuracy() == 0.0


def test_accuracy_du_champion_lue_depuis_son_run(registry):
    registry(alias=FakeVersion(3), accuracy=0.812)
    assert evaluate.get_champion_accuracy() == pytest.approx(0.812)


def test_une_panne_mlflow_ne_vaut_pas_zero(registry):
    """Serveur injoignable, droits refusés : MLflow lève la même classe
    d'exception qu'un alias absent. Retourner 0.0 dans ce cas ferait promouvoir
    un challenger que personne n'a comparé à personne. Une porte de qualité
    doit fermer quand elle ne sait pas."""
    registry(alias=None, erreur=INTERNAL_ERROR)
    with pytest.raises(MlflowException):
        evaluate.get_champion_accuracy()


# --- promote_challenger -------------------------------------------------------

def test_la_promotion_cible_le_run_mesure(registry, monkeypatch):
    """Le run gagnant est enregistré puis aliasé. Aucune recherche de « la
    version la plus élevée » : c'est exactement le modèle qui vient d'être
    mesuré qui part en production."""
    client = registry(alias=FakeVersion(1), accuracy=0.79)
    enregistres = []

    def faux_register(model_uri, name):
        enregistres.append((model_uri, name))
        return FakeVersion(7)

    monkeypatch.setattr(evaluate.mlflow, "register_model", faux_register)
    assert evaluate.promote_challenger("run-abc") == "7"
    assert enregistres == [("runs:/run-abc/model", evaluate.MODEL_NAME)]
    assert client.promue == "7"


# --- Le DAG, lu sans Airflow --------------------------------------------------

@pytest.fixture(scope="module")
def dag_source() -> str:
    return DAG_FILE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def decorateurs(dag_source) -> dict[str, ast.Call]:
    """Associe chaque fonction décorée du DAG à son décorateur @dag/@task."""
    arbre = ast.parse(dag_source)
    trouves = {}
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.FunctionDef):
            for deco in noeud.decorator_list:
                if isinstance(deco, ast.Call):
                    trouves[noeud.name] = deco
    return trouves


def test_le_dag_est_planifie_et_ne_rattrape_pas(decorateurs):
    """`catchup=True` (le défaut) sur un start_date ancien déclencherait d'un
    coup toutes les exécutions manquées — des dizaines de ré-entraînements
    simultanés au premier démarrage."""
    args = {kw.arg: kw.value for kw in decorateurs["churn_retrain_pipeline"].keywords}
    assert ast.literal_eval(args["schedule"]) == "@weekly"
    assert ast.literal_eval(args["catchup"]) is False


@pytest.mark.parametrize("tache", ["train_challenger", "evaluate_and_promote"])
def test_chaque_tache_a_une_politique_de_reprise(decorateurs, tache):
    """Le piège du chapitre : sans `retries`, un échec hebdomadaire passe
    inaperçu et le champion vieillit en silence."""
    args = {kw.arg: kw.value for kw in decorateurs[tache].keywords}
    assert "retries" in args, f"{tache} n'a aucune politique de reprise"
    assert ast.literal_eval(args["retries"]) >= 1
    assert "retry_delay" in args


def test_l_evaluation_depend_de_l_entrainement(dag_source):
    """La dépendance TaskFlow : evaluate reçoit le résultat de train, donc
    Airflow ne la démarre pas avant la fin de l'entraînement."""
    assert "evaluate_and_promote(train_challenger())" in dag_source
