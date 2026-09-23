"""Corrigé des tests du Chapitre 10.

Un workflow GitHub Actions ne se teste pas vraiment en local : il faudrait un
runner. Ce qu'on peut verrouiller, en revanche, ce sont les décisions qui
rendent le pipeline utile — et dont l'oubli ne déclenche aucune erreur, juste
un faux sentiment de sécurité.

Les six pièges couverts ici :
    1. pas de déclencheur `pull_request` → la CI protège après le merge
    2. pas de `needs: test` → l'image se construit même sur du code cassé
    3. pas de garde `if` sur main → chaque pull request publie une image
    4. pas de `pip install -e .` → ModuleNotFoundError sur le runner
    5. un secret écrit en clair → fuite garantie tôt ou tard
    6. un modèle réentraîné dans le job de build → l'image embarque un binaire
       que les tests n'ont jamais vu

Lancer depuis `chapitre-10/solution/` :  pytest -v
"""

import re
from pathlib import Path

import pytest
import yaml

WORKFLOW = (
    Path(__file__).resolve().parents[1] / "solution" / ".github" / "workflows" / "ci.yml"
)


@pytest.fixture(scope="module")
def ci() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def declencheurs(ci) -> dict:
    """PyYAML lit le `on:` nu du YAML comme le booléen True (norme YAML 1.1) :
    la clé du dictionnaire est donc `True`, pas la chaîne "on". Piège récurrent
    dès qu'on parse un workflow GitHub Actions en Python."""
    return ci.get("on") or ci[True]


def test_le_workflow_existe_au_bon_endroit():
    """GitHub ne regarde qu'un seul dossier : .github/workflows/."""
    assert WORKFLOW.is_file()
    assert WORKFLOW.parent.as_posix().endswith(".github/workflows")


def test_la_ci_se_declenche_sur_les_pull_requests(declencheurs):
    """Le piège du chapitre. Sur `push` seul, le badge est vert et rien n'a
    jamais empêché un code cassé d'être mergé."""
    assert "pull_request" in declencheurs
    assert "main" in declencheurs["pull_request"]["branches"]


def test_le_build_attend_le_succes_des_tests(ci):
    assert ci["jobs"]["build-and-push"]["needs"] == "test"


def test_le_build_ne_publie_que_depuis_main(ci):
    """Sans cette garde, chaque pull request pousserait une image sur GHCR."""
    assert ci["jobs"]["build-and-push"]["if"] == "github.ref == 'refs/heads/main'"


def test_le_runner_reconstruit_ce_qui_est_gitignore(ci):
    """Un runner clone un dépôt nu : ni paquet installé, ni données, ni modèle.
    Les trois étapes doivent précéder pytest, dans cet ordre."""
    etapes = "\n".join(str(step) for step in ci["jobs"]["test"]["steps"])
    assert "pip install -e ." in etapes
    assert "dvc pull" in etapes
    assert etapes.index("dvc pull") < etapes.index("churn_predictor.train")
    assert etapes.index("churn_predictor.train") < etapes.index("pytest")


def test_les_deux_tags_sont_pousses(ci):
    """Le SHA pour le rollback exact (Ch. 16), `latest` pour Kubernetes (Ch. 12)."""
    tags = ci["jobs"]["build-and-push"]["steps"][-1]["with"]["tags"]
    assert "${{ github.sha }}" in tags
    assert ":latest" in tags


def test_aucun_secret_en_clair():
    """Tout ce qui ressemble à un identifiant doit passer par `secrets.*`.
    Un mot de passe commité reste dans l'historique même après suppression."""
    contenu = WORKFLOW.read_text(encoding="utf-8")
    for ligne in contenu.splitlines():
        if re.search(r"(password|token|secret_access_key)\s*:", ligne, re.IGNORECASE):
            assert "secrets." in ligne, f"secret potentiellement en clair : {ligne.strip()}"


def test_le_modele_teste_est_celui_qui_part_dans_l_image(ci):
    """Deux runners jetables ne partagent aucun disque. Le `.pkl` validé par
    `pytest` doit voyager par un artefact — sinon le build réentraîne, et
    publie une image contenant un modèle qu'aucun test n'a vu."""
    upload = [
        step
        for step in ci["jobs"]["test"]["steps"]
        if str(step.get("uses", "")).startswith("actions/upload-artifact")
    ]
    download = [
        step
        for step in ci["jobs"]["build-and-push"]["steps"]
        if str(step.get("uses", "")).startswith("actions/download-artifact")
    ]
    assert upload and download, "le .pkl ne circule pas entre les deux jobs"
    assert upload[0]["with"]["name"] == download[0]["with"]["name"]

    build = "\n".join(str(step) for step in ci["jobs"]["build-and-push"]["steps"])
    assert "churn_predictor.train" not in build, "le build réentraîne au lieu de télécharger"
