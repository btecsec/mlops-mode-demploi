# Exercice — Chapitre 4

**Starter fourni** : l'état exact laissé par `chapitre-03` — un dépôt avec
`data/` et `exploration.ipynb`, rien d'autre.

**Objectif** : reproduire seul la restructuration complète du chapitre.

## À faire, sans regarder `solution/`

1. Écrire le `.gitignore` **en premier**, avant tout commit. Il doit couvrir :
   environnements virtuels, `__pycache__`, notebooks checkpoints, `data/raw/*.csv`,
   `models/*.pkl`, `.env`.
2. Créer et activer un `venv`, y installer `pandas`, `scikit-learn`, `pytest`,
   puis figer `requirements.txt` avec `pip freeze --exclude-editable`.
3. Créer l'arborescence `src/churn_predictor/`, `notebooks/`, `tests/`, `models/`,
   `data/raw/` et y déplacer le notebook et le CSV.
4. Écrire un `pyproject.toml` minimal, puis `pip install -e .`.
5. Écrire `config.py` (chemins calculés depuis `ROOT_DIR`), `data.py`
   (`load_raw_data()`, `churn_rate()`), `__init__.py` et `train.py`.
6. Écrire `tests/test_data.py` et le faire passer.
7. Produire quatre commits atomiques en Conventional Commits.

## Questions

1. Pourquoi `ROOT_DIR = Path(__file__).resolve().parents[2]` et pas `Path(".")` ?
2. À quoi sert exactement `--exclude-editable` dans `pip freeze` ? Que se
   passe-t-il au build Docker (Ch. 6) si on l'oublie ?
3. Que se passe-t-il si on supprime `pyproject.toml` puis qu'on relance `pytest` ?
   Reproduisez l'erreur, lisez-la, puis remettez le fichier.
4. Pourquoi le test sur le taux de churn utilise-t-il une fourchette
   (`0.20 < rate < 0.30`) plutôt que l'égalité exacte à 0,2654 ?

## Bonus

Ajoutez un test qui échoue volontairement (par exemple `assert df.shape == (7000, 21)`),
vérifiez que `pytest` le signale, puis corrigez-le. Un test qu'on n'a jamais vu
échouer n'est pas un test, c'est une décoration.

## Critères de réussite

- `python -m churn_predictor.train` affiche `26.5%` depuis n'importe quel dossier.
- `pytest` passe au vert.
- `git status` est propre : ni CSV, ni `venv/`, ni `__pycache__` en attente.
- `git log --oneline` raconte une histoire lisible en quatre lignes.

## Piège de ce chapitre

Commiter le CSV « juste pour que ça marche sur GitHub ». Un dépôt Git gonfle
pour toujours, même après suppression du fichier. La bonne réponse n'est pas
« je l'enlève après », c'est le `.gitignore` de l'étape 1.
