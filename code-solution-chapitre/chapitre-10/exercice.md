# Exercice — Chapitre 10

**Starter fourni** : l'état exact laissé par `chapitre-08` — API conteneurisée,
MLflow en place, données versionnées par DVC. Tout se lance encore à la main.

**Objectif** : écrire le workflow GitHub Actions qui relance les tests sur
chaque pull request, construit l'image Docker, et ne la publie que depuis `main`.

## À faire, sans regarder `solution/`

1. Créer `.github/workflows/ci.yml` avec un job `test` déclenché sur `push`
   **et** sur `pull_request` vers `main`.
2. Dans ce job : checkout, Python 3.14, installation des dépendances, puis
   `pytest`. Réfléchir à ce qui manque sur un runner par rapport à votre
   machine — trois choses, toutes gitignorées depuis le Chapitre 4.
3. Ajouter un job `build-and-push` qui dépend du premier et ne s'exécute que
   depuis `main`. Connexion à GHCR, build, push avec deux tags : le SHA du
   commit et `latest`.
4. Faire voyager le `.pkl` du job `test` vers le job `build-and-push`
   (`actions/upload-artifact` puis `actions/download-artifact`) au lieu de le
   réentraîner. Le job de build ne doit plus avoir besoin ni de Python, ni de
   DVC.
5. Pousser sur une branche, ouvrir une pull request, observer l'onglet
   « Checks ».
6. Après merge sur `main`, tirer l'image publiée sur GHCR et la lancer.
7. Vérifier `/health` puis `/predict` depuis un terminal : `curl` sous bash,
   `curl.exe` sous PowerShell, payload dans un fichier `client.json`.

## Questions

1. Cassez volontairement un test (changez `7043` en `7000` dans
   `test_data.py`), ouvrez une pull request. Le check passe-t-il au rouge, et
   une image est-elle malgré tout publiée ?
2. Retirez `pip install -e .` du job `test` et relancez. Lisez l'erreur en
   entier : à quelle ligne du test échoue-t-elle, et pourquoi si tôt ?
3. Retirez `needs: test` du job `build-and-push`, puis poussez un commit qui
   casse un test sur `main`. Que se retrouve-t-il publié sur GHCR ?
4. Le modèle est entraîné avec `random_state=42`, donc reproductible.
   Qu'est-ce qui peut malgré tout différer entre le `.pkl` du job `test` et
   celui qu'un job `build-and-push` réentraînerait ?
5. Que se passerait-il si `if: github.ref == 'refs/heads/main'` disparaissait,
   sur un dépôt qui reçoit dix pull requests par jour ?
6. `secrets.GITHUB_TOKEN` n'est déclaré nulle part dans les paramètres du dépôt.
   D'où vient-il, et combien de temps est-il valide ?

## Bonus

- Ajouter une étape de lint (`ruff check .`) avant `pytest`, et la rendre
  bloquante. Puis discuter : faut-il bloquer un merge sur un problème de style ?
- Mesurer le temps gagné par le passage d'artefact : comparer la durée du job
  `build-and-push` avec et sans réentraînement.
- Passer `retention-days` de 5 à 1, puis tenter de retélécharger l'artefact
  d'un run de la semaine passée. Quelle conséquence pour un rollback (Ch. 16) ?
- Ajouter une matrice de versions Python (`3.12`, `3.13`, `3.14`) au job `test`.
  Combien de runs cela déclenche-t-il par pull request ?
- Faire échouer le pipeline volontairement sur un secret manquant, et lire ce
  que GitHub affiche (ou masque) dans les logs.

## Critères de réussite

- Une pull request avec un test cassé affiche un check rouge.
- L'image tirée depuis GHCR répond `{"status":"ok"}` sur `/health` et renvoie une
  prédiction sur `/predict`, sous bash comme sous PowerShell.
- Aucune image n'est publiée depuis une pull request.
- Un merge sur `main` produit deux tags sur GHCR : le SHA et `latest`.
- Aucun identifiant n'apparaît en clair dans `ci.yml`.

## Piège de ce chapitre

`on: push` sans `pull_request`. Le pipeline tourne, il est vert, et la CI
n'a jamais empêché quoi que ce soit — elle valide du code déjà mergé.
