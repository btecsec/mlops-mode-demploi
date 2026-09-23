"""Corrigé des tests du Chapitre 9.

Le chapitre sort les données du disque local : le remote DVC devient un bucket
S3, joignable depuis n'importe quelle machine authentifiée. Deux choses doivent
être vraies en même temps — le remote distant est bien déclaré, et aucune clé
d'accès n'a fini dans un fichier suivi par Git.

Ces tests ne touchent jamais le réseau : ils relisent des fichiers texte. Ils
passent donc sans compte AWS, sans DVC installé, et sans le moindre euro dépensé.

Lancer depuis `chapitre-09/solution/` :  pytest -v
"""

import configparser
import re
from pathlib import Path

import pytest

SOLUTION = Path(__file__).resolve().parents[1] / "solution"
CONFIG = SOLUTION / ".dvc" / "config"
CONFIG_LOCAL_IGNORE = SOLUTION / ".dvc" / ".gitignore"
REQUIREMENTS = SOLUTION / "requirements.txt"

# Une clé d'accès AWS commence par AKIA (utilisateur) ou ASIA (session).
CLE_ACCES = re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")
CHAMPS_SECRETS = ("access_key_id", "secret_access_key", "session_token")


@pytest.fixture(scope="module")
def config() -> configparser.ConfigParser:
    """`.dvc/config` est un fichier INI : configparser le lit tel quel."""
    parser = configparser.ConfigParser()
    parser.read(CONFIG, encoding="utf-8")
    return parser


def test_un_remote_s3_est_declare(config):
    """Sans remote distant, les données restent prisonnières d'un seul disque
    et la CI du Chapitre 10 n'a rien à récupérer."""
    urls = [config[section].get("url", "") for section in config.sections()]
    assert any(url.startswith("s3://") for url in urls), (
        "aucun remote s3:// dans .dvc/config — le remote du Chapitre 8 est "
        "toujours le seul déclaré"
    )


def test_le_remote_s3_precise_sa_region(config):
    """Sans région explicite, le client S3 tombe sur us-east-1 par défaut et
    échoue avec une erreur de redirection peu bavarde."""
    for section in config.sections():
        if config[section].get("url", "").startswith("s3://"):
            assert config[section].get("region"), (
                "remote S3 sans `region` : ajouter "
                "`dvc remote modify <nom> region eu-west-3`"
            )


def test_aucune_cle_aws_dans_le_fichier_versionne(config):
    """Le piège du chapitre : `dvc remote modify` sans `--local` écrit la clé
    dans `.dvc/config`, qui part au premier `git push`."""
    contenu = CONFIG.read_text(encoding="utf-8")
    assert not CLE_ACCES.search(contenu), (
        "une clé d'accès AWS est écrite en clair dans .dvc/config — la révoquer "
        "dans IAM avant toute autre chose"
    )
    for section in config.sections():
        for champ in CHAMPS_SECRETS:
            assert champ not in config[section], (
                "%s présent dans .dvc/config : refaire la commande avec --local"
                % champ
            )


def test_la_config_locale_reste_hors_de_git():
    """`.dvc/config.local` accueille les deux clés. Il n'est utile que s'il est
    effectivement ignoré — c'est `dvc init` qui pose cette règle."""
    regles = CONFIG_LOCAL_IGNORE.read_text(encoding="utf-8").split()
    assert "/config.local" in regles


def test_l_extra_s3_est_epingle():
    """`dvc` seul ne sait pas parler à S3 : le client arrive avec l'extra."""
    requirements = REQUIREMENTS.read_text(encoding="utf-8")
    assert "dvc[s3]" in requirements, (
        "requirements.txt épingle `dvc` sans l'extra s3 : `dvc push` échouerait "
        "sur un remote s3:// avec « URL is not supported »"
    )
