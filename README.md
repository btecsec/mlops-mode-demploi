# MLOps, Mode d'Emploi — le code

Dépôt d'accompagnement du livre **MLOps, Mode d'Emploi — Le guide complet pour
déployer, automatiser et superviser vos modèles de Machine Learning avec Docker,
Kubernetes, MLflow, CI/CD et le Cloud**.

Un seul projet fil rouge, du notebook au cluster Kubernetes surveillé :
**prédiction du désabonnement client d'un opérateur télécom** (dataset
*Telco Customer Churn*, 7 043 clients, 21 colonnes, cible binaire `Churn`).

📖 **Le livre est disponible sur Amazon :
[MLOps, Mode d'Emploi](https://www.amazon.fr/dp/B0HKSX43P7)**

Ce dépôt ne contient **que du code**. Le texte du livre n'y est pas, et n'y sera
pas : il est protégé par le droit d'auteur.

## Deux dossiers, deux usages

| Dossier | Ce que c'est | Pour qui |
|----|----|----|
| [`code-solution-chapitre/`](code-solution-chapitre/) | Un dossier par chapitre : l'énoncé du TP, son corrigé exécutable, ses tests | **Le lecteur.** C'est le dépôt auquel le livre renvoie. |
| [`code-complet/mlops-churn-project/`](code-complet/mlops-churn-project/) | Le projet vivant, tous les chapitres empilés, dans l'état où il tourne après le Chapitre 17 | Qui veut voir l'arrivée sans faire le trajet |

La différence tient en une phrase. Le second est **un** projet ; le premier en
contient **dix-sept**, un par étape, chacun complet et lançable seul.

### Le dépôt des corrigés

```text
code-solution-chapitre/
├── bootstrap.py       # installe le dataset dans les chapitres qui en ont besoin
├── chapitre-01/
│   ├── README.md      # ce que le chapitre ajoute, comment lancer la solution
│   ├── exercice.md    # les étapes attendues, sans le corrigé
│   ├── solution/      # le projet entier à la fin du chapitre
│   └── tests/         # les tests du chapitre
├── chapitre-02/
└── ... jusqu'à chapitre-17/
```

`solution/` n'est jamais un fragment : c'est le projet complet tel qu'il tourne à
la fin du chapitre. On entre donc dans n'importe quel chapitre et on lance les
tests, sans avoir fait les précédents.

Son [README](code-solution-chapitre/README.md) porte le sommaire des dix-sept
chapitres, les prérequis par outil et le détail du démarrage.

## Démarrage rapide

```bash
git clone https://github.com/btecsec/mlops-mode-demploi.git
cd mlops-mode-demploi/code-solution-chapitre

# Le dataset n'est pas commité : il s'installe en une commande.
python bootstrap.py all

# Un chapitre au hasard, ici le 5 — l'API FastAPI.
cd chapitre-05/solution
python -m venv venv
source venv/Scripts/activate      # Git Bash sous Windows
# source venv/bin/activate        # macOS / Linux
pip install -r requirements.txt
pip install -e .

python -m churn_predictor.train
pytest -v
uvicorn churn_predictor.app:app --reload
```

Sous PowerShell, l'activation devient `venv\Scripts\Activate.ps1`.

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

## Où le fil rouge arrive

```text
   Données (DVC) ────────────┐
                             ▼
  ┌─────────── Airflow : DAG hebdomadaire (Ch. 11) ───────────┐
  │   train.py ──▶ MLflow Tracking ──▶ Registry @champion     │
  └──────────────────────▲───────────────────┬────────────────┘
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

## Sur les workflows CI de ce dépôt

Les deux dossiers portent chacun un `.github/workflows/ci.yml`. Ce sont les
**livrables du Chapitre 10**, à lire et à rejouer dans votre propre dépôt — pas
la CI de celui-ci. GitHub Actions ne lit que le `.github/workflows/` placé à la
racine, et il n'y en a pas ici : rien ne se déclenche sur ce dépôt, et c'est
voulu.

## Licence

Le code est publié sous licence **MIT** — voir [LICENSE](LICENSE).
Lisez-le, modifiez-le, republiez-le, réutilisez-le dans un projet commercial,
sans demander quoi que ce soit à personne.

Le texte du livre, lui, n'est pas sous cette licence, et ce dépôt n'en contient
aucun extrait.
