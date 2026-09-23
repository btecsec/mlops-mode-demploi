"""Corrigé des tests du Chapitre 16.

Ce qu'on vérifie ici n'est pas « est-ce que ça marche » mais « est-ce qu'un
auditeur pourrait le contredire » : l'empreinte est-elle stable, irréversible,
propre à cette installation ? L'identifiant réel a-t-il vraiment disparu des
journaux ? La ligne d'audit répond-elle bien aux quatre questions (qui, quand,
quel client, quelle version) ?

Le sel de test est posé par `conftest.py`, avant tout import.

Lancer depuis `chapitre-16/solution/` :  pytest -v
"""

import csv
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from churn_predictor import app as app_module
from churn_predictor import audit
from churn_predictor.privacy import PSEUDONYM_SALT, pseudonymize

SOLUTION = Path(__file__).resolve().parents[1] / "solution"
POLICY = SOLUTION / "iam" / "policy-readonly-registry.json"

client = TestClient(app_module.app)

PAYLOAD = {
    "gender": "Female", "SeniorCitizen": 0, "Partner": "No", "Dependents": "No",
    "tenure": 2, "PhoneService": "Yes", "MultipleLines": "No",
    "InternetService": "Fiber optic", "OnlineSecurity": "No", "OnlineBackup": "No",
    "DeviceProtection": "No", "TechSupport": "No", "StreamingTV": "No",
    "StreamingMovies": "No", "Contract": "Month-to-month", "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check", "MonthlyCharges": 95.5, "TotalCharges": 191.0,
}
CUSTOMER_ID = "7590-VHVEG"   # premier client du dataset Telco


@pytest.fixture
def journaux(tmp_path, monkeypatch):
    """Redirige les deux journaux vers des fichiers temporaires."""
    audit_log = tmp_path / "logs" / "audit_log.csv"
    monkeypatch.setattr(audit, "AUDIT_LOG", audit_log)
    monkeypatch.setattr(app_module, "PREDICTIONS_LOG", tmp_path / "logs" / "pred.csv")
    return audit_log


# --- pseudonymize() -----------------------------------------------------------

def test_l_empreinte_est_stable():
    """Le même client doit donner la même empreinte, sinon impossible de
    recouper deux requêtes du même client — l'intérêt même de pseudonymiser
    plutôt que d'anonymiser."""
    assert pseudonymize(CUSTOMER_ID) == pseudonymize(CUSTOMER_ID)


def test_deux_clients_donnent_deux_empreintes():
    assert pseudonymize("7590-VHVEG") != pseudonymize("5575-GNVDE")


def test_l_empreinte_ne_contient_pas_l_identifiant():
    """L'évidence à vérifier quand même : un préfixe oublié dans le format
    de sortie et toute la pseudonymisation ne sert plus à rien."""
    empreinte = pseudonymize(CUSTOMER_ID)
    assert CUSTOMER_ID not in empreinte
    assert "7590" not in empreinte


def test_l_empreinte_depend_du_sel():
    """Sans sel, l'espace des identifiants Telco (7043 valeurs connues) se
    parcourt en une seconde : le hash seul ne protégerait rien."""
    attendu_sans_sel = hashlib.sha256(CUSTOMER_ID.encode()).hexdigest()[:16]
    assert pseudonymize(CUSTOMER_ID) != attendu_sans_sel


def test_l_empreinte_est_bien_un_sha256_sale():
    attendu = hashlib.sha256(f"{CUSTOMER_ID}{PSEUDONYM_SALT}".encode()).hexdigest()[:16]
    assert pseudonymize(CUSTOMER_ID) == attendu


def test_le_format_est_court_et_lisible():
    empreinte = pseudonymize(CUSTOMER_ID)
    assert len(empreinte) == 16
    assert all(c in "0123456789abcdef" for c in empreinte)


# --- L'audit trail ------------------------------------------------------------

def test_l_audit_repond_aux_quatre_questions(journaux):
    """Qui, quand, quel client, quelle version — une ligne doit suffire."""
    reponse = client.post(
        "/predict",
        json=PAYLOAD,
        headers={"X-Customer-Id": CUSTOMER_ID, "X-Caller": "crm-batch"},
    )
    assert reponse.status_code == 200

    with open(journaux, encoding="utf-8") as f:
        ligne = next(csv.DictReader(f))

    assert ligne["caller"] == "crm-batch"
    assert ligne["customer_hash"] == pseudonymize(CUSTOMER_ID)
    assert ligne["timestamp"].endswith("+00:00")     # UTC explicite, pas d'heure locale
    assert ligne["model_version"]


def test_l_identifiant_client_n_apparait_jamais_en_clair(journaux):
    """Le piège du chapitre. Une fois qu'un identifiant en clair a atterri dans
    un log, il y reste : sauvegardes, exports, outils tiers."""
    client.post("/predict", json=PAYLOAD, headers={"X-Customer-Id": CUSTOMER_ID})
    assert CUSTOMER_ID not in journaux.read_text(encoding="utf-8")


def test_le_journal_de_drift_ne_contient_aucune_identite(journaux, tmp_path):
    """Deux journaux, deux publics. Celui du Chapitre 15 sert au drift : il
    n'a aucune raison de contenir un identifiant, même pseudonymisé."""
    client.post("/predict", json=PAYLOAD, headers={"X-Customer-Id": CUSTOMER_ID})
    drift_log = (tmp_path / "logs" / "pred.csv").read_text(encoding="utf-8")
    assert CUSTOMER_ID not in drift_log
    assert pseudonymize(CUSTOMER_ID) not in drift_log


def test_une_prediction_reste_tracee_meme_si_le_registry_repond_pas(journaux, monkeypatch):
    """Perdre la trace est irréversible ; perdre le numéro de version ne l'est
    pas. En cas de Registry injoignable, on écrit la ligne quand même."""
    audit.get_champion_version.cache_clear()
    monkeypatch.setattr(
        audit, "MlflowClient", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("down"))
    )
    audit.log_prediction_audit(CUSTOMER_ID, {"probability": 0.5}, "crm-batch")
    audit.get_champion_version.cache_clear()

    with open(journaux, encoding="utf-8") as f:
        assert next(csv.DictReader(f))["model_version"] == audit.VERSION_INCONNUE


# --- IAM : le moindre privilège -----------------------------------------------

@pytest.fixture(scope="module")
def policy() -> dict:
    return json.loads(POLICY.read_text(encoding="utf-8"))


def test_la_policy_n_autorise_qu_une_action(policy):
    """Moindre privilège : ce compte invoque l'endpoint, un point c'est tout.
    Ni le supprimer, ni en créer un autre, ni lire le reste du compte cloud."""
    statement = policy["Statement"][0]
    assert statement["Effect"] == "Allow"
    assert statement["Action"] == ["sagemaker:InvokeEndpoint"]


def test_la_policy_cible_une_ressource_precise(policy):
    """`"Resource": "*"` est la façon la plus courante de transformer un droit
    de lecture en droit sur tout le compte."""
    resource = policy["Statement"][0]["Resource"]
    assert resource != "*"
    assert resource.endswith("endpoint/churn-predictor-endpoint")


# --- Le rollback --------------------------------------------------------------

def test_le_rollback_ne_supprime_aucune_version():
    """`set_registered_model_alias` déplace un pointeur. Un rollback qui
    supprimerait la version quittée ne serait pas réversible — or c'est
    justement sous pression qu'on se trompe de numéro."""
    source = (SOLUTION / "scripts" / "rollback_model.py").read_text(encoding="utf-8")
    assert "set_registered_model_alias" in source
    assert "delete_model_version" not in source
    # Le script doit dire comment annuler ce qu'il vient de faire.
    assert "Pour annuler ce rollback" in source


def test_le_sel_n_a_pas_de_valeur_par_defaut():
    """Un sel par défaut serait partagé par toutes les installations : les
    empreintes deviendraient comparables entre elles, donc ré-identifiables
    par recoupement."""
    source = (SOLUTION / "src" / "churn_predictor" / "privacy.py").read_text(encoding="utf-8")
    assert 'os.environ["PSEUDONYM_SALT"]' in source
    assert "os.getenv" not in source


def test_le_sel_n_est_pas_commite():
    """`.env.example` est de la documentation, `.env` est un secret."""
    gitignore = (SOLUTION / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore
    assert not (SOLUTION / ".env").exists()
