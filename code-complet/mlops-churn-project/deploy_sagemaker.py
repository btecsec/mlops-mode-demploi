import mlflow
from mlflow.deployments import get_deploy_client

from churn_predictor.config import MLFLOW_TRACKING_URI

# Sans cette ligne, "models:/churn-predictor@champion" est cherché dans le
# backend par défaut de MLflow, pas dans le Registry du Chapitre 7.
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

# "sagemaker:/<région>" : un client de déploiement MLflow, pas un client boto3.
client = get_deploy_client("sagemaker:/eu-west-1")

client.create_deployment(
    name="churn-predictor-endpoint",
    model_uri="models:/churn-predictor@champion",  # le Registry du Chapitre 7
    config={
        # L'image de l'Étape 1 et le rôle de l'Étape 2. 123456789012 est un
        # numéro de compte fictif : remplacez-le par le vôtre, que rend
        # `aws sts get-caller-identity --query Account --output text`.
        "image_url": "123456789012.dkr.ecr.eu-west-1.amazonaws.com/mlflow-pyfunc:3.15.2",
        "execution_role_arn": "arn:aws:iam::123456789012:role/mlops-sagemaker-execution",
        "instance_type": "ml.m5.large",
        "instance_count": 1,
        "timeout_seconds": 900,  # la création dépasse souvent les 300 s par défaut
    },
)