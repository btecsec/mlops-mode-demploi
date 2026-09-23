"""Corrigé des tests du Chapitre 6, version exécutable sans Docker.

Le vrai test du chapitre est `test_container_smoke.sh` (build + run + curl).
Ces assertions-ci vérifient les quatre décisions du Dockerfile qui, oubliées,
produisent un container qui démarre sans erreur et ne sert rien — le pire cas.

Lancer depuis `chapitre-06/solution/` :  pytest -v
"""

from pathlib import Path

import pytest

SOLUTION = Path(__file__).resolve().parents[1] / "solution"
DOCKERFILE = (SOLUTION / "Dockerfile").read_text(encoding="utf-8")
DOCKERIGNORE = (SOLUTION / ".dockerignore").read_text(encoding="utf-8").split()


def test_uvicorn_ecoute_sur_toutes_les_interfaces():
    """Le piège du chapitre : sans --host 0.0.0.0, le container est injoignable
    depuis l'hôte alors que `docker ps` l'affiche fièrement `Up`."""
    assert "--host" in DOCKERFILE and "0.0.0.0" in DOCKERFILE


def test_requirements_copie_avant_le_code():
    """Ordre des COPY = efficacité du cache : le code change à chaque
    itération, pas les dépendances."""
    assert DOCKERFILE.index("COPY requirements.txt") < DOCKERFILE.index("COPY src/")


def test_image_de_base_slim():
    assert "python:3.14-slim" in DOCKERFILE


def test_modele_embarque_dans_l_image():
    """Le build ne réentraîne rien : il copie le .pkl déjà produit."""
    assert "COPY models/" in DOCKERFILE


@pytest.mark.parametrize("exclu", [".git", "venv/", "notebooks/", "tests/", "data/"])
def test_dockerignore_exclut_le_superflu(exclu):
    """data/ n'a rien à faire dans l'image : elle sert le modèle, pas le CSV."""
    assert exclu in DOCKERIGNORE
