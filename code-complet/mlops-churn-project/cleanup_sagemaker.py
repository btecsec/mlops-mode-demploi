"""Supprime tout ce que le déploiement SageMaker a créé.

`aws sagemaker delete-endpoint` n'emporte que l'endpoint. Le déploiement en
avait créé quatre : l'endpoint, sa configuration, le modèle SageMaker et
l'archive du modèle déposée sur S3. Les trois dernières ne coûtent presque
rien, mais elles s'empilent à chaque relance du TP et brouillent la lecture de
la console.

`archive=False` demande la suppression complète ; `archive=True` conserverait
la configuration et le modèle. Les deux exigent `synchronous=True`.

MLflow crée ses ressources dans l'ordre modèle, configuration d'endpoint,
endpoint, et `delete_deployment` remonte la chaîne dans l'autre sens : il
demande l'endpoint, y lit sa configuration, y lit son modèle. Un déploiement
qui échoue avant la fin rompt la chaîne, et ce qui existait déjà devient
inatteignable — `DescribeEndpoint` répond `Could not find endpoint`, la
fonction s'arrête là et le modèle survit à tous les nettoyages. D'où le second
passage : les ressources orphelines se retrouvent à leur préfixe de nom, sans
passer par l'endpoint.

Deux ressources restent hors de portée de ce script, parce qu'elles ne
viennent pas du déploiement — elles facturent au gigaoctet-mois, et il faut
les supprimer à la main :

    # l'image de service poussée à l'étape 1, environ 1 Go
    aws ecr delete-repository --repository-name mlflow-pyfunc --force --region eu-west-1

    # le bucket que MLflow a créé pour y poser le modèle
    aws s3 rb s3://mlflow-sagemaker-eu-west-1-<numéro-de-compte> --force

Et le rôle d'exécution, qui ne coûte rien mais reste un droit ouvert :

    aws iam detach-role-policy --role-name mlops-sagemaker-execution --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
    aws iam delete-role --role-name mlops-sagemaker-execution
"""

import argparse

import boto3
from botocore.exceptions import ClientError
from mlflow.deployments import get_deploy_client

# Volontairement redéclarés plutôt qu'importés de deploy_sagemaker : importer
# ce module exécuterait son set_tracking_uri, et un script de nettoyage n'a
# aucune raison de toucher au Registry.
APP_NAME = "churn-predictor-endpoint"
DEFAULT_REGION = "eu-west-1"


def supprimer_endpoint(region: str) -> None:
    """Supprime endpoint, configuration, modèle et archive S3 d'un coup."""
    client = get_deploy_client(f"sagemaker:/{region}")
    try:
        client.delete_deployment(
            APP_NAME,
            config={"archive": False, "synchronous": True},
        )
    except ClientError as erreur:
        # Le seul cas normal : le déploiement a échoué, ou le ménage a déjà été
        # fait. Toute autre erreur (droits, région) doit remonter telle quelle.
        if erreur.response["Error"]["Code"] != "ValidationException":
            raise
        print(f"Aucun endpoint '{APP_NAME}' : rien à supprimer par ce chemin.")
        return
    print(f"Endpoint '{APP_NAME}' supprimé, avec sa configuration et son modèle.")


def supprimer_orphelins(region: str) -> None:
    """Balaie les configurations et modèles que la chaîne n'atteint plus."""
    sagemaker = boto3.client("sagemaker", region_name=region)

    # Les noms sont listés avant toute suppression : un paginateur qu'on vide
    # en cours de route saute des pages.
    configurations = [
        element["EndpointConfigName"]
        for page in sagemaker.get_paginator("list_endpoint_configs").paginate(
            NameContains=APP_NAME
        )
        for element in page["EndpointConfigs"]
    ]
    modeles = [
        element["ModelName"]
        for page in sagemaker.get_paginator("list_models").paginate(
            NameContains=APP_NAME
        )
        for element in page["Models"]
    ]

    # Dans cet ordre : une configuration désigne un modèle, on retire le
    # pointeur avant la cible.
    for nom in configurations:
        sagemaker.delete_endpoint_config(EndpointConfigName=nom)
        print(f"Configuration d'endpoint orpheline supprimée : {nom}")
    for nom in modeles:
        sagemaker.delete_model(ModelName=nom)
        print(f"Modèle orphelin supprimé : {nom}")

    if not configurations and not modeles:
        print("Aucune ressource orpheline.")


def cleanup(region: str = DEFAULT_REGION) -> None:
    """Nettoie le déploiement, réussi ou raté."""
    supprimer_endpoint(region)
    supprimer_orphelins(region)
    print(
        "Vérifiez que les trois listes reviennent vides :\n"
        f"    aws sagemaker list-endpoints --region {region}\n"
        f"    aws sagemaker list-endpoint-configs --region {region}\n"
        f"    aws sagemaker list-models --region {region}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default=DEFAULT_REGION)
    args = parser.parse_args()
    cleanup(args.region)
