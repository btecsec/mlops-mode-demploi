# Chapitre 14 — Cloud et MLOps : AWS, GCP, Azure

Le même modèle, déjà dans le Registry depuis le Chapitre 7, part sur un endpoint
managé SageMaker. Sans réentraînement, sans toucher à `train.py`, et sans
remplacer la stack maison — les deux coexistent, c'est le sujet du chapitre.

## Ce que le chapitre ajoute

| Fichier | Rôle |
|----|----|
| `deploy_sagemaker.py` | Déploie `models:/churn-predictor@champion` sur un endpoint managé |
| `cleanup_sagemaker.py` | Supprime endpoint, configuration, modèle SageMaker et archive S3 |
| `trust-policy.json` | Qui a le droit d'endosser le rôle d'exécution : le service SageMaker, personne d'autre |
| `requirements-sagemaker.txt` | `mlflow[extras]`, `boto3`, `sagemaker` — isolés du reste |
| `tests/test_deploy_script.py` | 15 tests, sans AWS, sans facture |

## ⚠️ Ce TP coûte de l'argent

Un endpoint SageMaker facture tant qu'il **existe**, actif ou non. Contrairement
à un Pod Kubernetes, qui ne consomme que des ressources déjà provisionnées
(Chapitre 13). L'étape de nettoyage n'est pas optionnelle, et `delete-endpoint`
seul n'y suffit pas : le déploiement a créé quatre ressources, et deux autres
dorment dans ECR et sur S3.

```bash
# endpoint + configuration d'endpoint + modèle SageMaker + archive S3,
# puis balayage des configurations et modèles qu'un déploiement raté
# laisse orphelins — créés avant l'endpoint, ils survivent à sa
# suppression parce que MLflow les cherche à travers lui
python cleanup_sagemaker.py --region eu-west-1

# les trois listes doivent revenir vides
aws sagemaker list-endpoints --region eu-west-1
aws sagemaker list-endpoint-configs --region eu-west-1
aws sagemaker list-models --region eu-west-1

# les deux dépôts de stockage, facturés au Go-mois
aws ecr delete-repository --repository-name mlflow-pyfunc --force --region eu-west-1
aws s3 rb s3://mlflow-sagemaker-eu-west-1-123456789012 --force

# le rôle : gratuit, mais un droit ouvert qu'on referme
aws iam detach-role-policy --role-name mlops-sagemaker-execution --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
aws iam delete-role --role-name mlops-sagemaker-execution
```

| Ressource | Créée à | Facture ? | Supprimée par |
|----|----|----|----|
| Endpoint | étape 5 | Oui, à l'heure, allumé ou non | `cleanup_sagemaker.py` |
| Configuration d'endpoint | étape 5 | Non | `cleanup_sagemaker.py` |
| Modèle SageMaker | étape 5 | Non | `cleanup_sagemaker.py` |
| Archive du modèle sur S3 | étape 5 | Oui, au Go-mois | `cleanup_sagemaker.py` |
| Image dans ECR | étape 2 | Oui, au Go-mois, environ 1 Go | `aws ecr delete-repository` |
| Bucket `mlflow-sagemaker-…` | étape 5 | Oui tant qu'il contient des objets | `aws s3 rb --force` |
| Rôle d'exécution | étape 4 | Non | `aws iam delete-role` |

## Lancer la solution

```bash
python ../../bootstrap.py 13
cd solution
pip install -r requirements.txt && pip install -e .
python -m churn_predictor.train
python -m churn_predictor.register      # il faut un champion à déployer
```

Puis la partie AWS, à part :

```bash
pip install -r requirements-sagemaker.txt
aws configure
aws sts get-caller-identity             # QUELLE identité va agir ? réflexe à prendre

# 1. l'image de service générique (elle ne contient PAS le modèle)
#    le démon Docker doit tourner : l'image est construite en local
mlflow sagemaker build-and-push-container
aws ecr describe-images --repository-name mlflow-pyfunc --region eu-west-1

# 1 bis. l'URI complète, que describe-images n'affiche pas : on la recompose
URI=$(aws ecr describe-repositories --repository-names mlflow-pyfunc --region eu-west-1 --query "repositories[0].repositoryUri" --output text)
TAG=$(aws ecr describe-images --repository-name mlflow-pyfunc --region eu-west-1 --query "imageDetails[0].imageTags[0]" --output text)
echo "$URI:$TAG"    # -> 123456789012.dkr.ecr.eu-west-1.amazonaws.com/mlflow-pyfunc:3.15.2

# 2. le rôle que SageMaker assume pour lire cette image et le modèle sur S3
aws iam create-role --role-name mlops-sagemaker-execution --assume-role-policy-document file://trust-policy.json
aws iam attach-role-policy --role-name mlops-sagemaker-execution --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
aws iam get-role --role-name mlops-sagemaker-execution --query "Role.Arn" --output text

# 3. le déploiement, qui consomme les deux valeurs ci-dessus
python deploy_sagemaker.py --region eu-west-1 \
  --image-url 123456789012.dkr.ecr.eu-west-1.amazonaws.com/mlflow-pyfunc:3.15.2 \
  --execution-role-arn arn:aws:iam::123456789012:role/mlops-sagemaker-execution
```

`aws sts get-caller-identity` économise un quart d'heure : il confirme quelle
identité sera réellement utilisée, avant une commande qui construit et pousse
une image dans ECR.

Sous `zsh` (macOS), les crochets de `mlflow[extras]` doivent être quotés, sinon
le shell les prend pour un motif de fichiers et refuse la commande. Le fichier
`requirements-sagemaker.txt` évite le problème.

## L'image ECR ne s'appelle pas comme votre modèle

`build-and-push-container` construit un serveur d'inférence MLflow **générique**,
poussé dans un repository nommé en dur `mlflow-pyfunc`, et tagué à la version de
MLflow — pas à celle du modèle. Chercher un tag `churn-predictor` dans ECR ne
donne donc rien, et c'est normal : le modèle n'entre jamais dans l'image. Il est
téléversé sur S3 au déploiement, puis monté dans le conteneur au démarrage. Une
seule image sert tous vos modèles.

Son URI ne s'affiche nulle part d'un bloc : `describe-images` connaît le tag et
le numéro de compte (`registryId`) mais pas la région, `describe-repositories`
connaît `repositoryUri` mais pas les tags. Les deux commandes ci-dessus les
collent, plutôt que de recopier quatre morceaux à la main.

Le rôle d'exécution n'est pas optionnel non plus. Omis, MLflow déduit un rôle de
l'identité appelante, ce qui suppose d'être déjà *dans* un rôle : depuis
l'utilisateur IAM du Chapitre 9, l'appel `iam:GetRole` échoue en `NoSuchEntity`.

## Interroger l'endpoint

```bash
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name churn-predictor-endpoint \
  --content-type application/json \
  --body '{"dataframe_records": [{"gender": "Female", "SeniorCitizen": 0, "Partner": "No", "Dependents": "No", "tenure": 2, "PhoneService": "Yes", "MultipleLines": "No", "InternetService": "Fiber optic", "OnlineSecurity": "No", "OnlineBackup": "No", "DeviceProtection": "No", "TechSupport": "No", "StreamingTV": "No", "StreamingMovies": "No", "Contract": "Month-to-month", "PaperlessBilling": "Yes", "PaymentMethod": "Electronic check", "MonthlyCharges": 95.5, "TotalCharges": 191.0}]}' \
  output.json
cat output.json
```

```json
{"predictions": [1]}
```

## Deux différences avec le Chapitre 5, et elles disent l'essentiel

- La requête est enveloppée dans `dataframe_records` : un serveur MLflow attend
  un tableau de lignes, pas un client isolé.
- La réponse est la sortie brute du modèle, pas le `{"churn": …, "probability":
  …}` de l'API maison — parce que l'endpoint sert le **modèle** du Registry, pas
  l'application FastAPI.

`predict_churn()`, qui traduit une probabilité en décision métier, reste de
votre côté. Un service managé fournit l'inférence ; l'habillage métier se code
toujours quelque part.

## Le Registry reste la source de vérité

`model_uri="models:/churn-predictor@champion"` : SageMaker n'a besoin de rien
savoir de l'entraînement. Il consomme la version que le Chapitre 11 a promue.
Repartir d'un `.pkl` local reconstruit pour l'occasion, c'est perdre la trace de
quelle version tourne réellement sur l'endpoint — et un test verrouille ce point.

Le déploiement passe par `create_deployment()`, jamais par `update_deployment()` :
écraser un endpoint en production doit être un geste explicite, pas l'effet de
bord d'un script relancé par distraction. Noter aussi le point d'entrée :
`mlflow.sagemaker.deploy()` a disparu avec MLflow 2.0, remplacé par
`mlflow.deployments.get_deploy_client("sagemaker:/<région>")`.

## Lancer les tests

```bash
pytest -v      # 93 tests (ch. 1 à 14)
```

Les 15 tests du chapitre lisent `deploy_sagemaker.py` et `cleanup_sagemaker.py`
en AST. Ils ne l'importent
pas — `mlflow.deployments` tire `boto3` et le SDK `sagemaker`, installés à part —
et surtout ils ne l'exécutent pas : un test qui crée une ressource facturée
n'est pas un test.

## Le piège du chapitre

Croire que « managé » veut dire « sans opérations ». Restent entièrement à votre
charge :

- les rôles IAM et les droits d'accès
- le suivi des coûts et les quotas
- le choix du type d'instance
- les mises à jour de version

Seule l'infrastructure sous-jacente — machines, réseau, disques — est gérée par
le fournisseur. « Managé » réduit le travail d'infrastructure, il ne le supprime
jamais.

## Ce que le chapitre ne tranche pas

Ni la stack maison ni le managé n'est « la bonne réponse ». Le choix dépend de
l'échelle, de la taille de l'équipe et de ce que coûte le verrouillage
fournisseur à cinq ans. Ce que les neuf chapitres précédents apportent, c'est de
pouvoir en discuter autrement que par dogme — et de reconnaître, derrière chaque
service managé, la brique qu'il remplace.

## Si ça ne marche pas

Les pannes rencontrées à ce TP, dans l'ordre où elles se déclarent. Le livre ne les déroule pas : elles vivent ici, à côté du code qui les provoque.

| Symptôme | Cause | Correctif |
|----|----|----|
| `AttributeError` sur `mlflow.sagemaker.deploy` | API retirée avec MLflow 2.0, encore montrée par d'innombrables tutoriels | `get_deploy_client("sagemaker:/<région>")` puis `create_deployment()` |
| `ValidationException: Deprecated instance type "T2"` | AWS a retiré la famille `ml.t2` de l'inférence temps réel | `ml.m5.large` ; le refus tombant tard, passer ensuite à l'Étape 7 |
| `NoSuchEntity` sur `iam:GetRole` | `execution_role_arn` omis : MLflow a tenté de déduire un rôle de l'identité appelante | Passer l'ARN de l'Étape 4 |
| `ModuleNotFoundError: No module named 'churn_predictor'` | Le `venv` n'est pas celui où le projet est installé en éditable | `pip install -e .` (Chapitre 4) |
| `RESOURCE_DOES_NOT_EXIST` | Aucune version `champion` dans le Registry que désigne `MLFLOW_TRACKING_URI` | L'enregistrer (Chapitre 7), ou pointer le bon serveur |
| `Could not find endpoint "churn-predictor-endpoint"` | Déploiement raté, ou ménage déjà fait | Aucun : le script l'avale et passe au balayage par nom |
