# Jeu de données du fil rouge

Ce dossier accueille le CSV **Telco Customer Churn** (`WA_Fn-UseC_-Telco-Customer-Churn.csv`,
7043 lignes, 21 colonnes, cible binaire `Churn`).

Le fichier n'est **pas** commité — c'est le piège classique du Chapitre 4 : un dépôt Git
n'est pas fait pour des fichiers volumineux, et l'historique n'oublie jamais.

## Le récupérer

1. Télécharger le dataset sur Kaggle :
   <https://www.kaggle.com/datasets?search=WA_Fn-UseC_-Telco-Customer-Churn.csv>
2. Déposer le `.csv` ici, sous le nom exact `WA_Fn-UseC_-Telco-Customer-Churn.csv`.
3. L'installer dans le chapitre voulu :

```bash
python bootstrap.py 5        # copie le CSV dans chapitre-05/solution/data/raw/
```

## Vérification

```bash
python -c "import pandas as pd; d=pd.read_csv('data/raw/WA_Fn-UseC_-Telco-Customer-Churn.csv'); print(d.shape)"
# (7043, 21)
```
