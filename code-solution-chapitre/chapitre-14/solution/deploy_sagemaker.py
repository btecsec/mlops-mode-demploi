"""Déploie le modèle `champion` du Registry MLflow sur un endpoint SageMaker.

Rien n'est réentraîné : le modèle enregistré au Chapitre 7 est consommé tel
quel. C'est tout l'intérêt du Registry — il reste la source de vérité, quel que
soit le mode de serving choisi derrière.

Prérequis :
    pip install -r requirements-sagemaker.txt
    aws configure
    aws sts get-caller-identity            # confirme QUELLE identité sera utilisée

    # 1. l'image de service générique, poussée dans le repository ECR
    #    "mlflow-pyfunc" et taguée à la version de MLflow (pas au nom du modèle)
    mlflow sagemaker build-and-push-container   # le démon Docker doit tourner
    aws ecr describe-images --repository-name mlflow-pyfunc --region eu-west-1

    # 1 bis. l'URI complète, que describe-images n'affiche pas : on la recompose
    URI=$(aws ecr describe-repositories --repository-names mlflow-pyfunc --region eu-west-1 --query "repositories[0].repositoryUri" --output text)
    TAG=$(aws ecr describe-images --repository-name mlflow-pyfunc --region eu-west-1 --query "imageDetails[0].imageTags[0]" --output text)
    echo "$URI:$TAG"        # -> la valeur attendue par --image-url

    # 2. le rôle que SageMaker assume pour lire cette image et le modèle sur S3
    aws iam create-role --role-name mlops-sagemaker-execution --assume-role-policy-document file://trust-policy.json
    aws iam attach-role-policy --role-name mlops-sagemaker-execution --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess

⚠️  Un endpoint SageMaker facture tant qu'il existe, actif ou non. Le supprimer
    en fin de TP n'est pas optionnel :

    aws sagemaker delete-endpoint --endpoint-name churn-predictor-endpoint
"""

import argparse
import os

import mlflow
from mlflow.deployments import get_deploy_client

from churn_predictor.config import MLFLOW_TRACKING_URI, MODEL_NAME

# Sans cette ligne, "models:/churn-predictor@champion" est cherché dans le
# backend par défaut de MLflow, pas dans le Registry du Chapitre 7 — le même
# piège que dans register.py et evaluate.py, une troisième fois.
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

APP_NAME = "churn-predictor-endpoint"
MODEL_URI = f"models:/{MODEL_NAME}@champion"

# La famille T2 a été retirée des endpoints temps réel : SageMaker répond
# ValidationException, Deprecated instance type "T2". ml.m5.large est la
# plus petite instance qui reste proposée pour de l'inférence temps réel.
DEFAULT_INSTANCE_TYPE = "ml.m5.large"
DEFAULT_REGION = "eu-west-1"


def deploy(
    region: str = DEFAULT_REGION,
    image_url: str | None = None,
    execution_role_arn: str | None = None,
    instance_type: str = DEFAULT_INSTANCE_TYPE,
) -> None:
    """Crée l'endpoint managé à partir de la version portant l'alias champion.

    `mlflow.sagemaker.deploy()` n'existe plus depuis MLflow 2.0 : le point
    d'entrée est le client de déploiement, dont le `target_uri` porte la
    région. `create_deployment()` échoue si l'endpoint existe déjà — c'est
    voulu : écraser un endpoint en production doit être un geste explicite,
    pas l'effet de bord d'un script relancé par distraction. Pour une mise à
    jour, `update_deployment()`.

    `execution_role_arn` n'est pas décoratif. Omis, MLflow déduit un rôle de
    l'identité appelante ; depuis un utilisateur IAM classique — celui du
    Chapitre 9 — l'appel `iam:GetRole` échoue en `NoSuchEntity`.
    """
    image_url = image_url or os.environ.get("MLFLOW_SAGEMAKER_DEPLOY_IMG_URL")
    execution_role_arn = execution_role_arn or os.environ.get("SAGEMAKER_EXECUTION_ROLE_ARN")
    if not image_url or not execution_role_arn:
        raise SystemExit(
            "Renseignez --image-url et --execution-role-arn (ou les variables "
            "MLFLOW_SAGEMAKER_DEPLOY_IMG_URL et SAGEMAKER_EXECUTION_ROLE_ARN). "
            "Les deux valeurs sortent des étapes 1 et 2 du TP."
        )

    client = get_deploy_client(f"sagemaker:/{region}")
    client.create_deployment(
        name=APP_NAME,
        model_uri=MODEL_URI,  # le Registry du Chapitre 7, pas un .pkl local
        config={
            "image_url": image_url,
            "execution_role_arn": execution_role_arn,
            "instance_type": instance_type,
            "instance_count": 1,
            # 300 s par défaut : la création d'un endpoint dépasse souvent ce délai.
            "timeout_seconds": 900,
        },
    )
    print(f"Endpoint '{APP_NAME}' créé depuis {MODEL_URI} ({region}, {instance_type}).")
    print(
        "Pensez à le supprimer en fin de TP :\n"
        f"    aws sagemaker delete-endpoint --endpoint-name {APP_NAME}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default=DEFAULT_REGION)
    parser.add_argument("--instance-type", default=DEFAULT_INSTANCE_TYPE)
    parser.add_argument(
        "--image-url",
        help="URI ECR de l'image mlflow-pyfunc, ex. "
        "123456789012.dkr.ecr.eu-west-1.amazonaws.com/mlflow-pyfunc:3.15.2",
    )
    parser.add_argument(
        "--execution-role-arn",
        help="ARN du rôle assumé par SageMaker, ex. "
        "arn:aws:iam::123456789012:role/mlops-sagemaker-execution",
    )
    args = parser.parse_args()
    deploy(args.region, args.image_url, args.execution_role_arn, args.instance_type)
