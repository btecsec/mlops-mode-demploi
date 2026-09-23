"""Corrigé des tests du Chapitre 8.

Le pointeur `.dvc` est le seul artefact du chapitre qui entre dans Git. S'il
est absent, incohérent, ou si le CSV se retrouve commité à côté, la traçabilité
promise à l'auditeur n'existe plus. Ces tests verrouillent les quatre points.

Ils tournent sans DVC installé : tout est vérifiable en lisant des fichiers
texte, y compris le hash — c'est le principe même de l'empreinte MD5.

Lancer depuis `chapitre-08/solution/` :  pytest -v
"""

import hashlib
from pathlib import Path

import pytest
import yaml

SOLUTION = Path(__file__).resolve().parents[1] / "solution"
CSV_NAME = "WA_Fn-UseC_-Telco-Customer-Churn.csv"
RAW_DIR = SOLUTION / "data" / "raw"
POINTEUR = RAW_DIR / f"{CSV_NAME}.dvc"


@pytest.fixture(scope="module")
def outs() -> dict:
    """La section `outs` du pointeur : hash, taille, chemin du fichier suivi."""
    contenu = yaml.safe_load(POINTEUR.read_text(encoding="utf-8"))
    return contenu["outs"][0]


def test_le_pointeur_existe():
    """Sans lui, `dvc pull` n'a rien à récupérer : le ticket de vestiaire
    n'a jamais été émis."""
    assert POINTEUR.is_file()


def test_le_pointeur_decrit_bien_le_csv(outs):
    assert outs["path"] == CSV_NAME
    assert outs["hash"] == "md5"
    assert outs["size"] > 0


def test_le_hash_correspond_au_fichier_local(outs):
    """Le cœur de DVC : le hash du pointeur et celui du fichier sur disque
    doivent coïncider. S'ils divergent, `dvc status` dirait `modified` —
    le dataset a bougé sans que personne l'ait déclaré."""
    csv = RAW_DIR / CSV_NAME
    if not csv.is_file():
        pytest.skip("CSV absent — lancer `python bootstrap.py 16` d'abord")

    empreinte = hashlib.md5(csv.read_bytes()).hexdigest()
    assert empreinte == outs["md5"]
    assert csv.stat().st_size == outs["size"]


def test_dvc_a_pose_sa_propre_regle_d_exclusion():
    """DVC génère `data/raw/.gitignore` ciblé sur le seul fichier suivi, en
    remplacement de la règle manuelle `data/raw/*.csv` du Chapitre 4. Si ce
    fichier manque, c'est que l'ancienne règle est encore en place."""
    regles = (RAW_DIR / ".gitignore").read_text(encoding="utf-8").split()
    assert f"/{CSV_NAME}" in regles


def test_un_remote_par_defaut_est_declare():
    """Sans remote par défaut, `dvc push` répond `no remote provided` et les
    données ne quittent jamais le poste — le piège du chapitre."""
    config = (SOLUTION / ".dvc" / "config").read_text(encoding="utf-8")
    assert "[core]" in config
    assert "remote = localstorage" in config
    assert 'remote "localstorage"' in config
