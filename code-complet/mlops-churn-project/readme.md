# Churn Predictor — Pipeline MLOps complet

Prédiction de désabonnement client (Telco Customer Churn), du notebook
à la production : API FastAPI, Docker, MLflow, DVC, CI/CD GitHub Actions,
orchestration Airflow, Kubernetes, Terraform, monitoring Evidently/Grafana.

C'est l'état du projet fil rouge à la fin du Chapitre 17 du livre
*MLOps, Mode d'Emploi*. Pour suivre le trajet étape par étape, voir
[`code-solution-chapitre/`](../../code-solution-chapitre/).

📖 **Le livre est disponible sur Amazon :
[MLOps, Mode d'Emploi](https://www.amazon.fr/dp/B0HKSX43P7)**

## Architecture

```text
   Données (DVC, remote S3) ─────┐
                                 ▼
  ┌──────────── Airflow : DAG hebdomadaire (Ch. 11) ────────────┐
  │   train.py ──▶ MLflow Tracking ──▶ Registry @champion       │
  └──────────────────────▲─────────────────────┬────────────────┘
                         │                     │
              drift Evidently (Ch. 15)         │ modèle promu
                         │                     ▼
   Client HTTP ──▶ Service K8s ──▶ Pods FastAPI (Ch. 5, 6, 12)
                         │                     │
                         │                     ├──▶ /metrics ──▶ Prometheus ──▶ Grafana
                         │                     └──▶ journal + audit trail (Ch. 15, 16)
                         │
              Cluster provisionné par Terraform (Ch. 13)
```

## Où trouver quoi

| Dossier | Contenu | Chapitre |
|----|----|----|
| `src/churn_predictor/` | Package Python : données, entraînement, API, audit, LLM | 4 à 17 |
| `tests/` | Tests `pytest` | 4 et suivants |
| `Dockerfile` | Image de l'API, utilisateur non root | 6, 16 |
| `.github/workflows/ci.yml` | Pipeline CI/CD | 10 |
| `airflow/` | DAG de ré-entraînement champion/challenger | 11 |
| `k8s/`, `churn-api-chart/` | Manifestes Kubernetes et chart Helm | 12 |
| `infra/` | Terraform (cluster GKE) | 13 |
| `deploy_sagemaker.py`, `cleanup_sagemaker.py` | Endpoint SageMaker et son nettoyage | 14 |
| `monitoring/` | Prometheus, Grafana, détection de drift | 15 |

Les TP des Chapitres 9, 13, 14 et 17 engagent des dépenses réelles :
voir l'avertissement du [README racine](../../README.md#avertissement-sur-les-coûts).
