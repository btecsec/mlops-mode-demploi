# Exercice — Chapitre 6

**Starter fourni** : l'état exact laissé par `chapitre-05` — API FastAPI
fonctionnelle en local, modèle entraîné.

**Objectif** : écrire le `Dockerfile` et le `.dockerignore` seul, builder
l'image, et vérifier que `/health` et `/predict` répondent depuis l'hôte.

## À faire, sans regarder `solution/`

1. Écrire `.dockerignore` avant le premier build.
2. Écrire le `Dockerfile` : image de base slim, `WORKDIR`, installation des
   dépendances, copie du code et du modèle, `PYTHONPATH`, `EXPOSE`, `CMD`.
3. `docker build -t churn-api:0.1 .`
4. `docker run -d -p 8000:8000 --name churn-api churn-api:0.1`
5. Vérifier `/health` puis `/predict` depuis l'hôte, avec le payload d'exemple.
6. Arrêter et supprimer le container.

## Questions

1. Enlevez `--host 0.0.0.0` du `CMD`, rebuildez, relancez. Le container est-il
   `Up` ? Que répond `curl` ? Pourquoi rien n'apparaît-il dans `docker logs` ?
2. Inversez l'ordre des `COPY` (code avant `requirements.txt`). Modifiez une
   ligne de `app.py`, rebuildez : combien de temps gagne ou perd le build ?
3. Comparez `docker images` entre `python:3.14` et `python:3.14-slim`.
4. Retirez `data/` du `.dockerignore` et rebuildez : de combien l'image grossit-elle,
   et pour quel bénéfice réel ?
5. Le modèle est copié dans l'image. Quel problème cela pose-t-il quand le
   modèle est réentraîné chaque semaine (Chapitre 11) ? Comment le Chapitre 12
   le résout-il ?

## Bonus

- Passer en **multi-stage build** : une étape qui entraîne le modèle, une étape
  finale qui ne garde que le runtime et le `.pkl`.
- Faire tourner le container avec un utilisateur non-root (`USER appuser`) —
  réflexe de sécurité qui revient au Chapitre 16.

## Critères de réussite

- `docker build` réussit sans erreur de version Python.
- `curl http://localhost:8000/health` renvoie `{"status":"ok"}` depuis l'hôte.
- `/predict` renvoie exactement `probability = 0.735` sur le payload d'exemple.
- `bash ../tests/test_container_smoke.sh` se termine sur `OK:`.

## Piège de ce chapitre

`--host 0.0.0.0` oublié. `127.0.0.1` dans un container ne désigne jamais la
machine hôte.
