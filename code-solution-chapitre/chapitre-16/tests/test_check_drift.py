"""Corrigé des tests du Chapitre 15.

Trois familles :

1. Le journal des prédictions — la Couche 2 ne mesure rien sans lui. On vérifie
   qu'un appel à `/predict` écrit bien une ligne, en-tête comprise.
2. La préparation des données comparées — c'est là que se cachent les faux
   positifs : une colonne comparée en texte d'un côté et en nombre de l'autre,
   ou présente d'un seul côté, produit une « dérive » qui n'existe pas.
3. Le calcul de drift lui-même — en skip si Evidently n'est pas installé
   (`requirements-monitoring.txt`, plusieurs centaines de Mo). L'import
   d'Evidently vit à l'intérieur de `check_drift()` précisément pour que le
   reste du module reste testable sans lui.

Lancer depuis `chapitre-15/solution/` :  pytest -v
"""

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from churn_predictor import app as app_module
from monitoring import check_drift as drift

client = TestClient(app_module.app)


@pytest.fixture
def journal(tmp_path, monkeypatch):
    """Redirige le journal vers un fichier temporaire.

    `app.py` et `check_drift.py` importent PREDICTIONS_LOG par valeur : patcher
    `config` ne suffirait pas, il faut patcher les deux modules qui s'en
    servent."""
    chemin = tmp_path / "logs" / "predictions_log.csv"
    monkeypatch.setattr(app_module, "PREDICTIONS_LOG", chemin)
    monkeypatch.setattr(drift, "PREDICTIONS_LOG", chemin)
    return chemin


@pytest.fixture
def payload() -> dict:
    return {
        "gender": "Female", "SeniorCitizen": 0, "Partner": "No",
        "Dependents": "No", "tenure": 2, "PhoneService": "Yes",
        "MultipleLines": "No", "InternetService": "Fiber optic",
        "OnlineSecurity": "No", "OnlineBackup": "No", "DeviceProtection": "No",
        "TechSupport": "No", "StreamingTV": "No", "StreamingMovies": "No",
        "Contract": "Month-to-month", "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": 95.5, "TotalCharges": 191.0,
    }


# --- Couche 1 : les métriques techniques --------------------------------------

def test_endpoint_metrics_expose():
    """Une ligne d'instrumentation, un endpoint que Prometheus lit nativement.
    S'il disparaît, le dashboard Grafana reste vert… et vide."""
    reponse = client.get("/metrics")
    assert reponse.status_code == 200
    assert "http_request" in reponse.text


# --- Couche 2 : le journal ----------------------------------------------------

def test_predict_alimente_le_journal(journal, payload):
    """Écrire `log_prediction` ne suffit pas : tant qu'elle n'est appelée nulle
    part, le journal est un fichier qui n'existe pas."""
    assert client.post("/predict", json=payload).status_code == 200
    assert journal.exists()

    lignes = pd.read_csv(journal)
    assert len(lignes) == 1
    assert "timestamp" in lignes.columns
    assert "probability" in lignes.columns
    assert lignes.loc[0, "Contract"] == "Month-to-month"


def test_le_journal_s_ajoute_sans_reecrire_l_entete(journal, payload):
    """Un en-tête réécrit à chaque requête, et `pd.read_csv` renvoie des lignes
    de texte au milieu des nombres."""
    for _ in range(3):
        client.post("/predict", json=payload)
    assert len(pd.read_csv(journal)) == 3


def test_journal_absent_message_explicite(journal):
    """Mesurer une dérive sans une seule requête reçue n'a pas de sens. Le
    script s'arrête proprement plutôt que de planter sur un FileNotFoundError
    incompréhensible."""
    with pytest.raises(SystemExit, match="Journal de prédictions introuvable"):
        drift.load_production()


def test_les_colonnes_du_journal_sont_retirees(journal, payload):
    """`timestamp` et `probability` n'existent pas dans le dataset
    d'entraînement : les comparer n'a aucun sens."""
    client.post("/predict", json=payload)
    production = drift.load_production()
    assert "timestamp" not in production.columns
    assert "probability" not in production.columns


# --- Préparation des données comparées ----------------------------------------

def test_la_baseline_est_nettoyee_comme_a_l_entrainement():
    """Sans le `to_numeric`, TotalCharges est du texte côté baseline et un
    nombre côté production : Evidently choisit deux tests statistiques
    différents pour la même colonne et annonce une dérive fantôme."""
    baseline = drift.load_baseline()
    assert pd.api.types.is_numeric_dtype(baseline["TotalCharges"])
    assert "customerID" not in baseline.columns
    assert "Churn" not in baseline.columns


def test_align_ne_garde_que_les_colonnes_communes():
    """Un champ ajouté au schéma d'entrée ne doit pas faire bondir le taux de
    dérive du jour au lendemain."""
    baseline = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
    production = pd.DataFrame({"c": [9], "a": [8], "d": [7]})

    ref, cur = drift.align(baseline, production)
    assert list(ref.columns) == list(cur.columns) == ["a", "c"]


def test_align_refuse_deux_schemas_disjoints():
    with pytest.raises(SystemExit, match="Aucune colonne commune"):
        drift.align(pd.DataFrame({"a": [1]}), pd.DataFrame({"z": [1]}))


def test_le_seuil_est_une_part_pas_un_pourcentage():
    """0.3 = 30 % des colonnes. Écrire 30 rendrait le seuil inatteignable et
    le ré-entraînement ne se déclencherait jamais — un bug parfaitement muet."""
    assert 0 < drift.DRIFT_THRESHOLD < 1


# --- Le calcul de drift, quand Evidently est installé -------------------------

def test_aucune_derive_sur_des_donnees_identiques(journal, monkeypatch):
    """Comparer la baseline à elle-même doit donner 0 %. Un chiffre non nul
    ici signifierait que la préparation des deux tableaux diverge."""
    pytest.importorskip("evidently", reason="voir requirements-monitoring.txt")

    baseline = drift.load_baseline()
    monkeypatch.setattr(drift, "load_production", lambda: baseline.copy())
    assert drift.check_drift() == 0.0


def test_une_derive_massive_est_detectee(journal, monkeypatch):
    """Un trafic dont dix colonnes sur dix-neuf ont changé de nature doit
    franchir le seuil, sinon le branchement du DAG ne servirait à rien.

    Dix, et pas trois : le seuil porte sur la *part* de colonnes dérivées. Ne
    faire bouger que les colonnes numériques donne 3/19, soit 16 % — en dessous
    des 30 % de DRIFT_THRESHOLD. Un tel test ne prouverait rien du branchement.
    """
    pytest.importorskip("evidently", reason="voir requirements-monitoring.txt")

    baseline = drift.load_baseline()
    derive = baseline.sample(500, random_state=42).copy()
    for colonne in ["tenure", "MonthlyCharges", "TotalCharges"]:
        derive[colonne] = derive[colonne] * 50 + 1000
    for colonne, valeur in {
        "Contract": "Two year",
        "InternetService": "Fiber optic",
        "PaymentMethod": "Mailed check",
        "OnlineSecurity": "Yes",
        "TechSupport": "Yes",
        "StreamingTV": "Yes",
        "PaperlessBilling": "No",
    }.items():
        derive[colonne] = valeur

    monkeypatch.setattr(drift, "load_production", lambda: derive)
    assert drift.check_drift() > drift.DRIFT_THRESHOLD


# --- Le branchement du DAG, lu sans Airflow -----------------------------------

def test_le_dag_ne_reentraine_que_sous_condition():
    """Le DAG du Chapitre 11 tournait à date fixe. Il se déclenche désormais sur
    un signal métier — la dérive mesurée — pas seulement sur le calendrier."""
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "solution" / "airflow" / "dags" / "churn_retrain_dag.py"
    ).read_text(encoding="utf-8")

    assert "@task.branch" in source
    assert "check_drift() > DRIFT_THRESHOLD" in source
    # Les deux branches doivent exister, sinon Airflow échoue sur un id de
    # tâche inconnu au moment du branchement.
    assert "def train_challenger" in source
    assert "def skip_retrain" in source
