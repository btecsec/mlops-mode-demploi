"""Corrigé des tests du Chapitre 16.

`deploy_sagemaker.py` ne peut pas être importé ici : `mlflow.deployments` tire
`boto3` et le SDK `sagemaker`, plusieurs centaines de mégaoctets installés à
part (`requirements-sagemaker.txt`). Et même importable, l'exécuter créerait
une ressource facturée — un test qui coûte de l'argent n'est pas un test.

On lit donc le script en AST. Ce qu'on vérifie n'a de toute façon rien à voir
avec AWS : c'est que le déploiement consomme bien le Registry MLflow du
Chapitre 7, et pas un fichier local reconstruit pour l'occasion.

Lancer depuis `chapitre-16/solution/` :  pytest -v
"""

import ast
from pathlib import Path

import pytest

SOLUTION = Path(__file__).resolve().parents[1] / "solution"
SCRIPT = SOLUTION / "deploy_sagemaker.py"


@pytest.fixture(scope="module")
def source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def arbre(source) -> ast.Module:
    return ast.parse(source)


@pytest.fixture(scope="module")
def appel_deploy(arbre) -> ast.Call:
    """L'appel à client.create_deployment(...), où qu'il vive."""
    for noeud in ast.walk(arbre):
        if (
            isinstance(noeud, ast.Call)
            and isinstance(noeud.func, ast.Attribute)
            and noeud.func.attr == "create_deployment"
        ):
            return noeud
    pytest.fail("aucun appel à create_deployment(...) trouvé")


@pytest.fixture(scope="module")
def config_deploy(appel_deploy) -> dict:
    """Le dictionnaire `config=` passé à create_deployment, clés seules."""
    for kw in appel_deploy.keywords:
        if kw.arg == "config":
            return {ast.literal_eval(k): v for k, v in zip(kw.value.keys, kw.value.values)}
    pytest.fail("create_deployment appelé sans config=")


def test_le_script_existe_et_est_du_python_valide(arbre):
    assert isinstance(arbre, ast.Module)


def test_le_modele_vient_du_registry_pas_d_un_fichier_local(source):
    """Le cœur du chapitre : SageMaker consomme le modèle versionné du
    Chapitre 7. Repartir d'un .pkl local, c'est perdre la trace de quelle
    version tourne réellement sur l'endpoint."""
    assert 'models:/{MODEL_NAME}@champion' in source or "models:/churn-predictor@champion" in source
    assert "churn_model.pkl" not in source


def test_l_alias_est_champion_pas_un_stage(source):
    """Les stages MLflow ("Production") sont l'ancienne API, abandonnée dès le
    Chapitre 7 au profit des alias."""
    assert "@champion" in source
    assert "/Production" not in source


def test_le_tracking_uri_est_fixe_avant_le_deploiement(source):
    """Sans set_tracking_uri, `models:/...@champion` est cherché dans le
    backend par défaut de MLflow : Registry vide, modèle introuvable. Même
    piège qu'au Chapitre 7, qu'au Chapitre 11, et une troisième fois ici."""
    assert "mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)" in source
    assert source.index("set_tracking_uri") < source.index("def deploy")


def test_l_api_de_deploiement_est_celle_qui_existe_encore(source):
    """`mlflow.sagemaker.deploy()` a disparu avec MLflow 2.0. Sur une
    installation récente elle lève AttributeError, alors que d'innombrables
    tutoriels la montrent encore."""
    assert "from mlflow.deployments import get_deploy_client" in source
    assert "mfs.deploy(" not in source
    assert "import mlflow.sagemaker" not in source


def test_la_region_passe_par_le_target_uri(source):
    """Le client de déploiement porte la région dans son URI de cible,
    "sagemaker:/<région>" — ce n'est pas un client boto3."""
    assert 'get_deploy_client(f"sagemaker:/{region}")' in source


def test_le_role_d_execution_est_explicite(config_deploy):
    """Omis, MLflow déduit un rôle de l'identité appelante : cela ne marche
    que depuis un rôle déjà assumé. Depuis l'utilisateur IAM du Chapitre 9,
    l'appel iam:GetRole échoue en NoSuchEntity."""
    assert "execution_role_arn" in config_deploy


def test_l_image_de_service_est_explicite(config_deploy):
    """L'image mlflow-pyfunc de l'étape 1. Sans elle, MLflow interroge ECR
    pour la déduire — une résolution silencieuse de plus à déboguer."""
    assert "image_url" in config_deploy


def test_le_type_d_instance_est_declare_et_valide(config_deploy, arbre):
    """Une instance non choisie, c'est une facture non choisie. Et la famille
    T2 a été retirée des endpoints temps réel : SageMaker la refuse."""
    assert "instance_type" in config_deploy
    assert "instance_count" in config_deploy
    litteraux = {
        n.value for n in ast.walk(arbre) if isinstance(n, ast.Constant) and isinstance(n.value, str)
    }
    assert not any(valeur.startswith("ml.t2.") for valeur in litteraux)


def test_le_script_rappelle_comment_supprimer_l_endpoint(source):
    """Un endpoint SageMaker facture tant qu'il existe, actif ou non. La
    commande de nettoyage doit être sous les yeux de qui lance le script."""
    assert "delete-endpoint" in source


def test_aucun_identifiant_aws_en_dur(source):
    """Les identifiants viennent d'`aws configure` ou d'un rôle IAM, jamais du
    code. Un secret commité reste dans l'historique même après suppression."""
    interdits = ["aws_access_key_id", "aws_secret_access_key", "AKIA"]
    for motif in interdits:
        assert motif not in source, f"identifiant potentiellement en dur : {motif}"


def test_les_dependances_lourdes_sont_isolees():
    """boto3, sagemaker et mlflow[extras] ne servent qu'à ce chapitre. Les
    mettre dans requirements.txt imposerait plusieurs centaines de Mo à tous
    les lecteurs des chapitres 4 à 12."""
    principal = (SOLUTION / "requirements.txt").read_text(encoding="utf-8")
    dedie = (SOLUTION / "requirements-sagemaker.txt").read_text(encoding="utf-8")
    assert "boto3" not in principal
    assert "boto3" in dedie and "sagemaker" in dedie
# ---------------------------------------------------------------------------
# Le script de nettoyage : la seule chose qui arrête la facture
# ---------------------------------------------------------------------------

CLEANUP = SOLUTION / "cleanup_sagemaker.py"


@pytest.fixture(scope="module")
def source_cleanup() -> str:
    return CLEANUP.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def appel_delete(source_cleanup) -> ast.Call:
    for noeud in ast.walk(ast.parse(source_cleanup)):
        if (
            isinstance(noeud, ast.Call)
            and isinstance(noeud.func, ast.Attribute)
            and noeud.func.attr == "delete_deployment"
        ):
            return noeud
    pytest.fail("aucun appel à delete_deployment(...) trouvé")


def test_le_nettoyage_supprime_les_ressources_associees(appel_delete):
    """archive=True conserverait la configuration d'endpoint et le modèle
    SageMaker, et archive=False exige synchronous=True. Un nettoyage à moitié
    fait laisse une facture à moitié ouverte."""
    config = next(kw.value for kw in appel_delete.keywords if kw.arg == "config")
    valeurs = {ast.literal_eval(k): ast.literal_eval(v)
               for k, v in zip(config.keys, config.values)}
    assert valeurs["archive"] is False
    assert valeurs["synchronous"] is True


def test_le_nettoyage_vise_le_meme_endpoint_que_le_deploiement(source, source_cleanup):
    """Deux noms qui divergent, et le script nettoie un endpoint qui n'existe
    pas pendant que le vrai continue de facturer."""
    assert 'APP_NAME = "churn-predictor-endpoint"' in source
    assert 'APP_NAME = "churn-predictor-endpoint"' in source_cleanup


def test_le_nettoyage_rappelle_les_ressources_qu_il_ne_touche_pas(source_cleanup):
    """L'image ECR et le bucket S3 facturent au Go-mois et ne viennent pas du
    déploiement : le script ne peut pas les supprimer, il doit au moins dire
    comment le faire."""
    for commande in ("aws ecr delete-repository", "aws s3 rb s3://mlflow-sagemaker",
                     "aws iam delete-role"):
        assert commande in source_cleanup, commande


def test_le_nettoyage_survit_a_l_endpoint_absent(source_cleanup):
    """Un déploiement qui échoue ne laisse aucun endpoint derrière lui, et
    `DescribeEndpoint` répond alors `Could not find endpoint`. Sans ce filet,
    le script s'arrête sur une trace au lieu de nettoyer ce qui reste."""
    arbre = ast.parse(source_cleanup)
    attrapes = [
        h.type.id
        for h in ast.walk(arbre)
        if isinstance(h, ast.ExceptHandler) and isinstance(h.type, ast.Name)
    ]
    assert "ClientError" in attrapes
    assert "ValidationException" in source_cleanup


def test_le_nettoyage_balaie_les_ressources_orphelines(source_cleanup):
    """MLflow crée le modèle avant l'endpoint et `delete_deployment` remonte
    depuis l'endpoint : un déploiement raté laisse un modèle que cette chaîne
    n'atteint plus. Il faut le retrouver par son nom."""
    arbre = ast.parse(source_cleanup)
    appels = {
        noeud.func.attr
        for noeud in ast.walk(arbre)
        if isinstance(noeud, ast.Call) and isinstance(noeud.func, ast.Attribute)
    }
    assert "delete_endpoint_config" in appels
    assert "delete_model" in appels
    assert "NameContains=APP_NAME" in source_cleanup
