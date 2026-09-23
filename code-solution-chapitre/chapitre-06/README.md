# Chapitre 6 — Docker : faire tourner l'API partout

L'API du Chapitre 5 devient une image : même comportement sur votre PC, sur
celui du collègue, et sur le cluster du Chapitre 12.

## Ce que le chapitre ajoute

| Fichier | Rôle |
|----|----|
| `.dockerignore` | écrit **avant** le premier build : image plus légère, build plus rapide |
| `Dockerfile` | `python:3.14-slim`, cache pip préservé, `--host 0.0.0.0` |
| `tests/test_container_smoke.sh` | build + run + `curl /health` + `/predict`, avec nettoyage |
| `tests/test_dockerfile.py` | vérifie les quatre décisions du Dockerfile, sans Docker |

Le code applicatif ne bouge pas d'une ligne : c'est exactement ce que Docker apporte.

## Lancer la solution

```bash
python ../../bootstrap.py 6
cd solution

# Le build n'entraîne rien : il embarque le modèle déjà sur disque.
python -m churn_predictor.train      # si models/churn_model.pkl n'existe pas

docker build -t churn-api:0.1 .
docker run -d -p 8000:8000 --name churn-api churn-api:0.1
docker ps
```

```text
CONTAINER ID   IMAGE            STATUS         PORTS
a1b2c3d4e5f6   churn-api:0.1    Up 2 seconds   0.0.0.0:8000->8000/tcp
```

## Vérifier depuis l'hôte

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" -d @../tests/payload_exemple.json
```

```json
{"status": "ok"}
{"churn": true, "probability": 0.735}
```

Même réponse qu'au Chapitre 5 — même code, même modèle, emballage différent.

## Nettoyer

```bash
docker stop churn-api && docker rm churn-api
```

## Lancer les tests

```bash
pytest -v                                # 16 tests, sans Docker
bash ../tests/test_container_smoke.sh    # le vrai smoke test, Docker requis
```

Le smoke test utilise le port `8001` pour ne pas entrer en conflit avec un
`uvicorn` lancé à la main à côté, et supprime son container même en cas d'échec.

## Deux choix de tag, deux conséquences

`0.1` est explicite. `latest` ne dit rien de ce qui tourne réellement — un vrai
problème le jour où il faut déboguer un incident ou faire un rollback (Ch. 16).

## Le piège qui coûte une soirée

```dockerfile
CMD ["uvicorn", "churn_predictor.app:app", "--port", "8000"]
```

Sans `--host 0.0.0.0`, uvicorn n'écoute que sur `127.0.0.1` — la boucle locale
**du container**. Le container démarre, `docker ps` affiche `Up`, le mapping de
port est correct, et `curl` depuis l'hôte renvoie *connection refused*. Rien ne
plante, rien ne log : c'est ce qui rend ce piège si long à diagnostiquer.

## Si ça ne marche pas

Les pannes rencontrées à ce TP, dans l'ordre où elles se déclarent. Le livre ne les déroule pas : elles vivent ici, à côté du code qui les provoque.

| Symptôme | Cause | Correctif |
|----|----|----|
| `Cannot connect to the Docker daemon` | Docker Desktop n'est pas lancé (Windows, macOS), ou le groupe `docker` n'est pas encore pris en compte (Linux) | Le démarrer ; sous Linux, refermer et rouvrir la session après le `usermod` |
| `COPY failed: ... models: no such file or directory` | Le modèle n'existe pas au moment du build | L'Étape 2 |
| Au build : `Could not find a version that satisfies the requirement` | Le tag Python de l'image est plus ancien que le `venv` qui a gelé `requirements.txt` | Aligner le `FROM` sur `python --version` |
| `docker ps` dit `Up`, mais `curl` reste sans réponse | uvicorn n'écoute que la boucle locale **du container** | `--host 0.0.0.0` : c'est le piège classique ci-dessous |
| `Bind for 0.0.0.0:8000 failed: port is already allocated` | Le port 8000 est déjà pris, souvent par l'`uvicorn` du Chapitre 5 | Le fermer, ou `docker run -p 8001:8000` |
