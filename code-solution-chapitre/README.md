# MLOps, Mode d'Emploi — code et corrigés des TP

[![CI](https://github.com/btecsec/mlops-mode-demploi/actions/workflows/ci.yml/badge.svg)](https://github.com/btecsec/mlops-mode-demploi/actions/workflows/ci.yml)
[![Licence MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)

Dépôt d'accompagnement du livre **MLOps, Mode d'Emploi — Le guide complet pour
déployer, automatiser et superviser vos modèles de Machine Learning avec Docker,
Kubernetes, MLflow, CI/CD et le Cloud**.
Un seul projet fil rouge, du notebook au cluster Kubernetes surveillé :
**prédiction du désabonnement client d'un opérateur télécom** (dataset
*Telco Customer Churn*, 7043 clients, 21 colonnes, cible binaire `Churn`).

## Comment ce dépôt est organisé

Un dossier par chapitre. Chacun contient le TP du livre, corrigé et exécutable :

```text
chapitre-XX/
├── README.md      # ce que le chapitre ajoute, comment lancer la solution
├── exercice.md    # les étapes attendues, sans le corrigé
├── solution/      # état complet et fonctionnel du fil rouge à la fin du chapitre
└── tests/         # tests corrigés du chapitre
```

`solution/` n'est pas un fragment : c'est le projet entier, tel qu'il tourne à la
fin du chapitre. On peut donc entrer dans n'importe quel chapitre et lancer les
tests sans avoir fait les précédents.

Chaque chapitre a son propre commit et son propre tag Git :

```bash
git tag                  # chapitre-01 ... chapitre-17
git show chapitre-07     # ce que le chapitre 7 ajoute exactement
git diff chapitre-06 chapitre-07 -- chapitre-07/solution
```

## Sommaire

| Chapitre | Sujet | Brique ajoutée au fil rouge |
|----|----|----|
| [01](chapitre-01/) | Le métier MLOps en vrai | Dépôt Git initialisé, `venv`, trois dépendances |
| [02](chapitre-02/) | Comprendre le ML avant de faire l'Ops | Notebook de démonstration des métriques, sur dix clients |
| [03](chapitre-03/) | Le dataset et le premier modèle | Dataset Telco, `exploration.ipynb`, premier `model.pkl` |
| [04](chapitre-04/) | Git et hygiène de projet | Package `src/churn_predictor/`, `.gitignore`, premiers tests |
| [05](chapitre-05/) | Construire une API de modèle | `train.py`, `predict.py`, API FastAPI `/health` + `/predict` |
| [06](chapitre-06/) | Docker | `Dockerfile`, `.dockerignore`, image `churn-api:0.1` |
| [07](chapitre-07/) | MLflow | Tracking des runs, Model Registry, alias `champion` |
| [08](chapitre-08/) | DVC | Dataset versionné, remote, retour à une version passée |
| [09](chapitre-09/) | Le cloud pour vos données | Compte AWS, bucket S3, remote DVC joignable depuis n'importe où |
| [10](chapitre-10/) | CI/CD | Workflow GitHub Actions : tests, build, push GHCR |
| [11](chapitre-11/) | Orchestration | DAG Airflow hebdomadaire, promotion champion/challenger |
| [12](chapitre-12/) | Kubernetes | Deployment, Service, ConfigMap, Secret, HPA, chart Helm |
| [13](chapitre-13/) | Terraform | Cluster managé en Infrastructure as Code, state distant |
| [14](chapitre-14/) | Cloud et MLOps | Déploiement du modèle du Registry sur un endpoint SageMaker |
| [15](chapitre-15/) | Monitoring | `/metrics` Prometheus, Grafana, drift Evidently |
| [16](chapitre-16/) | Sécurité et gouvernance | Pseudonymisation, audit trail, IAM, rollback |
| [17](chapitre-17/) | Portfolio et LLMOps | README portfolio, LangChain, LLM-as-a-judge |

Les Chapitres 1 et 2 n'utilisent pas le dataset : `bootstrap.py` ne l'installe
qu'à partir du Chapitre 3.

## Prérequis

| Outil | Version | À partir du chapitre |
|----|----|----|
| Python | ≥ 3.10 | 1 |
| Git | ≥ 2.30 | 1 |
| Docker | ≥ 24 | 6 |
| minikube + kubectl + Helm | récents | 12 |
| Terraform | ≥ 1.5 | 13 |

Airflow (Chapitre 11) ne s'installe pas nativement sous Windows : passer par WSL2
ou par l'image Docker officielle.

## Démarrage rapide

```bash
# 1. le dataset, jamais commité (voir data/raw/README.md)
python bootstrap.py all

# 2. un chapitre au hasard, ici le 5
cd chapitre-05/solution
python -m venv venv
source venv/Scripts/activate      # Git Bash sous Windows
# source venv/bin/activate        # macOS / Linux
pip install -r requirements.txt
pip install -e .

# 3. entraîner, tester, servir
python -m churn_predictor.train
pytest -v
uvicorn churn_predictor.app:app --reload
```

Sous PowerShell, l'activation devient `venv\Scripts\Activate.ps1`.

Chaque `solution/` déclare `testpaths = ["../tests"]` dans son `pyproject.toml` :
un simple `pytest` lancé depuis `solution/` va chercher les tests du chapitre.

## Architecture visée à la fin du livre

```text
   Données (DVC) ────────────┐
                             ▼
  ┌─────────── Airflow : DAG hebdomadaire (Ch. 11) ───────────┐
  │   train.py ──▶ MLflow Tracking ──▶ Registry @champion    │
  └──────────────────────▲───────────────────┬───────────────┘
                         │                   │
              drift Evidently (Ch. 15)       │ modèle promu
                         │                   ▼
   Client HTTP ──▶ Service K8s ──▶ Pods FastAPI (Ch. 5-6-12)
                         │                   │
                         │                   ├──▶ /metrics ──▶ Prometheus ──▶ Grafana
                         │                   └──▶ journal + audit trail (Ch. 15-16)
                         │
              Cluster provisionné par Terraform (Ch. 13)
```

## Avertissement sur les coûts

**Les TP des Chapitres 9, 13, 14 et 17 engagent des dépenses réelles.** Compte AWS
et bucket S3 au 9, cluster Google Kubernetes Engine au 13, endpoint SageMaker au
14, appels à une API de LLM au 17. Ces ressources sont facturées à l'heure, et
elles continuent de l'être tant qu'elles ne sont pas détruites — y compris si vous
avez fermé le terminal.

Chaque chapitre concerné se termine par son étape de destruction : `terraform
destroy`, `cleanup_sagemaker.py`, `aws s3 rb --force`. Elle n'est pas optionnelle.
Posez une alerte de budget avant de commencer, le Chapitre 9 montre comment.

## Licence

Le code de ce dépôt est publié sous licence **MIT** — voir [LICENSE](LICENSE).
Lisez-le, modifiez-le, republiez-le, réutilisez-le dans un projet commercial,
sans demander quoi que ce soit à personne.

Le texte du livre, lui, n'est pas sous cette licence : il est protégé par le droit
d'auteur, et ce dépôt n'en contient aucun extrait.
