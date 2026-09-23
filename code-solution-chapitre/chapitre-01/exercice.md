# Exercice — Chapitre 1

**Starter fourni** : rien. C'est le premier chapitre, on part d'un dossier vide.

**Objectif** : installer un environnement de travail propre et versionné. Pas
de données, pas de modèle — juste le terrain, correctement préparé.

## À faire, sans regarder `solution/`

1. Vérifier que `python --version` répond en 3.10 ou plus, et que `git --version` répond.
2. Créer le dépôt : `mkdir mlops-churn-project && cd mlops-churn-project && git init`.
3. Créer un `venv` à la racine du projet et l'activer.
4. Y installer `pandas`, `scikit-learn` et `jupyter`.
5. Vérifier l'installation :
   `python -c "import pandas, sklearn; print(pandas.__version__, sklearn.__version__)"`.

## Questions guidées

1. Comment savez-vous, à l'invite du terminal, que le `venv` est bien activé ?
2. Que se passe-t-il si vous lancez `pip install pandas` **avant** d'activer le `venv` ?
   Où le paquet atterrit-il ?
3. Pourquoi ne pas installer Docker, MLflow et Kubernetes dès maintenant, puisqu'ils
   serviront de toute façon plus tard ?
4. Le dossier `venv/` doit-il être commité dans Git ? Pourquoi ?
   *(la réponse complète arrive au Chapitre 4, mais l'intuition doit déjà être là)*
5. Sous Windows, quelle est la différence de syntaxe entre Git Bash et PowerShell pour
   activer le `venv` — et pour couper une commande longue sur plusieurs lignes ?

## Critères de réussite

- `git status` répond depuis `mlops-churn-project/` sans erreur.
- Le prompt du terminal affiche `(venv)`.
- `python -c "import pandas, sklearn"` ne lève aucune exception.
- `pytest ../tests -v` passe les trois tests.

## Piège de ce chapitre

Vouloir tout installer d'un coup — Docker, Kubernetes, MLflow, trois clouds.
Un outil par chapitre, et jamais avant d'avoir buté sur le problème qu'il résout.
