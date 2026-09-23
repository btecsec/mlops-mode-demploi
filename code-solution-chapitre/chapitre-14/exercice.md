# Exercice — Chapitre 14

**Starter fourni** : l'état exact laissé par `chapitre-13` — stack maison
complète, cluster provisionné par Terraform, modèle promu dans le Registry
MLflow.

**Objectif** : déployer ce même modèle sur un endpoint managé, puis argumenter
le choix entre les deux modes d'exploitation pour ce projet précis.

## ⚠️ Attention aux coûts

Un endpoint SageMaker facture tant qu'il existe, actif ou non. Ne sautez pas
l'étape 7. Si vous n'avez pas de compte AWS, les questions 1, 5, 6, 7 et 8 se
traitent sans rien déployer.

## À faire, sans regarder `solution/`

1. Installer les dépendances AWS **hors** de `requirements.txt`. Réfléchir à
   pourquoi elles ne doivent pas y aller.
2. S'authentifier, vérifier l'identité utilisée, puis
   `mlflow sagemaker build-and-push-container`. Retrouver l'image dans ECR avec
   `aws ecr describe-images` : sous quel nom de repository, et sous quel tag ?
   En déduire l'URI complète de l'image, que cette commande n'affiche pas.
3. Créer le rôle d'exécution que SageMaker assumera, et n'y attacher que ce
   qu'il faut pour lire l'image ECR et le modèle sur S3.
4. Écrire `deploy_sagemaker.py` : il doit consommer le modèle du Registry, pas
   un fichier local. Choisir explicitement le type d'instance, l'image et le
   rôle d'exécution.
5. Interroger l'endpoint avec `aws sagemaker-runtime invoke-endpoint` et
   comparer la réponse à celle de votre `/predict` du Chapitre 5.
6. Supprimer **toutes** les ressources créées, pas seulement l'endpoint.
   Listez-les d'abord, sur papier, avant de chercher les commandes.
7. Produire un tableau comparatif argumenté stack maison vs managé **pour ce
   projet** — pas en général.

## Questions

1. Le TP ne relance jamais `train.py`. Pourquoi est-ce possible, et qu'est-ce
   que cela dit du rôle du Model Registry depuis le Chapitre 7 ?
2. Comparez la réponse de l'endpoint et celle de votre `/predict`. Laquelle un
   développeur d'application mobile préfère-t-il consommer, et pourquoi ?
3. Retirez `mlflow.set_tracking_uri(...)` du script et relancez. Quelle erreur,
   et à quel chapitre l'avez-vous déjà rencontrée ?
4. Remplacez `create_deployment()` par `update_deployment()` et relancez le
   script deux fois de suite. Que se passe-t-il dans chaque cas ? Lequel
   préférez-vous en production, et pourquoi ?
5. Le repository ECR s'appelle `mlflow-pyfunc` et non `churn-predictor`, et
   son tag est un numéro de version de MLflow. Qu'est-ce que cela vous apprend
   sur ce que contient — et ne contient pas — cette image ? Où se trouve le
   modèle pendant que l'endpoint tourne ?
6. Estimez le coût mensuel d'un `ml.m5.large` laissé allumé. Comparez-le au
   coût d'un Pod supplémentaire sur le cluster du Chapitre 13.
7. Listez, pour ce projet, ce qui reste à votre charge malgré le « managé ».
   Combien de ces éléments aviez-vous déjà en tête avant de lire le chapitre ?
8. Votre entreprise utilise déjà BigQuery pour toute son analytique. Cela
   change-t-il votre recommandation entre AWS, GCP et Azure ? Sur quel critère
   exactement ?

## Bonus

- Refaire l'exercice sur Vertex AI ou Azure ML. Combien de lignes de code
  changent réellement, une fois le modèle dans le Registry ?
- Piloter la création de l'endpoint avec Terraform (`aws_sagemaker_endpoint`)
  plutôt qu'avec le SDK Python. Qu'y gagne-t-on ? Qu'y perd-on ?
- Brancher SageMaker Model Monitor sur l'endpoint et comparer ce qu'il détecte
  à ce que fera Evidently au Chapitre 15.
- Étendre `cleanup_sagemaker.py` au dépôt ECR, au bucket et au rôle IAM, en
  boto3 plutôt qu'en AWS CLI. Que faire quand une des six ressources a déjà
  été supprimée à la main ?

## Critères de réussite

- L'endpoint répond une prédiction sur un client réel du dataset.
- Le script pointe sur `models:/churn-predictor@champion`, jamais sur un `.pkl`.
- Le rôle d'exécution et l'image ECR sont passés explicitement, pas déduits.
- Aucun identifiant AWS n'apparaît dans le code.
- Les dépendances AWS ne sont pas dans `requirements.txt`.
- L'endpoint est supprimé en fin de TP, vérifié par
  `aws sagemaker list-endpoints`.
- `list-endpoint-configs` et `list-models` reviennent vides eux aussi, et le
  dépôt ECR comme le bucket `mlflow-sagemaker-…` ont disparu.
- `cleanup_sagemaker.py` va au bout même sans endpoint : un déploiement
  interrompu laisse un modèle que la suppression de l'endpoint n'atteint
  pas, le script le retrouve par son nom.
- Le tableau comparatif tranche pour **ce** projet, avec des arguments chiffrés.

## Piège de ce chapitre

« Managé » ne veut pas dire « sans opérations ». IAM, coûts, quotas, types
d'instance et montées de version restent à votre charge — seule l'infrastructure
sous-jacente est gérée par le fournisseur.
