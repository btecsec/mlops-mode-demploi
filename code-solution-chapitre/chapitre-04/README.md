# Chapitre 4 — Git et hygiène de projet

Le notebook fouillis du Chapitre 3 devient un projet Python structuré,
versionné et testé.

## Ce que le chapitre ajoute

| Fichier | Rôle |
|----|----|
| `.gitignore` | posé **avant** le premier commit sérieux — un fichier commité par erreur ne s'efface jamais vraiment |
| `pyproject.toml` | rend `src/churn_predictor/` installable, donc importable depuis `tests/` |
| `requirements.txt` | figé par `pip freeze --exclude-editable` |
| `src/churn_predictor/config.py` | tous les chemins, calculés une fois, jamais en dur ailleurs |
| `src/churn_predictor/data.py` | le chargement et la baseline, sortis du notebook, devenus testables |
| `src/churn_predictor/train.py` | point d'entrée en ligne de commande (squelette, complété au Ch. 5) |
| `notebooks/exploration.ipynb` | le notebook du Ch. 3, relégué à son vrai rôle : un brouillon |
| `tests/test_data.py` | premier garde-fou automatisé |

## Contenu

```text
chapitre-04/
├── README.md
├── exercice.md
├── solution/
│   ├── .gitignore
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── data/raw/          # le CSV, jamais commité
│   ├── models/
│   ├── notebooks/exploration.ipynb
│   └── src/churn_predictor/{__init__.py, config.py, data.py, train.py}
└── tests/
    └── test_data.py
```

## Lancer la solution

```bash
python ../../bootstrap.py 4
cd solution
python -m venv venv
source venv/Scripts/activate      # PowerShell : venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .                  # sans ça : ModuleNotFoundError dans pytest
python -m churn_predictor.train
```

```text
Taux de désabonnement (baseline métier) : 26.5%
```

Même résultat que le notebook du Chapitre 3, mais en une commande, depuis
n'importe quel dossier du projet.

## Lancer les tests

```bash
pytest -v
```

```text
../tests/test_data.py::test_dataset_shape PASSED
../tests/test_data.py::test_churn_rate_is_realistic PASSED
```

## Le détail qui coince toujours

`pip install -e .` n'est pas optionnel. Sans lui, `src/churn_predictor/` reste
un simple dossier : `pytest` échoue sur `ModuleNotFoundError: No module named
'churn_predictor'`, et aucun `sys.path.append` bricolé ne rendra ça propre.

## Historique Git attendu

```text
test: add baseline checks on dataset shape and churn rate
refactor: move exploration notebook into notebooks/
feat: extract data loading into churn_predictor package
chore: add gitignore for venv, data, models and secrets
```

Quatre commits **atomiques** : une intention par commit, lisible sans ouvrir le diff.

## Si ça ne marche pas

Les pannes rencontrées à ce TP, dans l'ordre où elles se déclarent. Le livre ne les déroule pas : elles vivent ici, à côté du code qui les provoque.

| Symptôme | Cause | Correctif |
|----|----|----|
| `ModuleNotFoundError: No module named 'churn_predictor'` | L'installation éditable n'a pas eu lieu, ou pas dans ce `venv` | `pip install -e .`, `venv` activé |
| `requirements.txt` illisible sur GitHub : `n u m p y = = 2 . 5 . 2` | La redirection `>` de PowerShell écrit de l'UTF-16, pas de l'UTF-8 | `pip freeze --exclude-editable \| Out-File -Encoding utf8 requirements.txt` |
| Une ligne `-e file:///C:/Users/...` dans `requirements.txt` | `pip freeze` sans `--exclude-editable` après l'installation éditable | Retirer la ligne, et garder le drapeau ensuite |
| En CI : `No matching distribution found for pywin32==312` | Le gel a capturé un paquet propre à Windows | Un marqueur d'environnement : `pywin32==312 ; sys_platform == "win32"` |
| `pip install -r requirements.txt` échoue sur la version de numpy | Le gel a été fait sous une autre version de Python | Reprendre la sortie de `python --version` dans le Dockerfile et le workflow |
