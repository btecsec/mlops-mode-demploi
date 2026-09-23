"""Corrigé des tests du Chapitre 1.

À ce stade du fil rouge, il n'existe ni package `churn_predictor`, ni dataset,
ni modèle : le seul livrable du chapitre est un environnement Python correct.
Ces trois tests vérifient exactement ça, rien de plus.

Lancer depuis `chapitre-01/solution/` :  pytest ../tests -v
"""

import importlib
import sys

import pytest


def test_version_de_python():
    """3.10 minimum : en dessous, scikit-learn récent et FastAPI (Ch. 5) décrochent."""
    assert sys.version_info >= (3, 10), (
        f"Python {sys.version_info.major}.{sys.version_info.minor} détecté — "
        "installez Python 3.10 ou plus récent."
    )


# `jupyter` est un méta-paquet : il n'expose pas de module `jupyter` importable.
# `jupyter_core` est la brique que toutes ses distributions installent.
@pytest.mark.parametrize("module", ["pandas", "sklearn", "jupyter_core"])
def test_bibliotheque_installee(module):
    """Les trois seules dépendances du chapitre, installées dans le venv actif."""
    try:
        importlib.import_module(module)
    except ImportError:
        pytest.fail(
            f"`{module}` introuvable. Activez le venv, puis : "
            "pip install pandas scikit-learn jupyter"
        )


def test_venv_est_actif():
    """sys.prefix diffère de sys.base_prefix uniquement dans un environnement virtuel."""
    assert sys.prefix != sys.base_prefix, (
        "Le venv ne semble pas activé : les paquets partiraient dans le Python global."
    )
