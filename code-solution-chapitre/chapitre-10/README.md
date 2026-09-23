# Chapitre 10 — CI/CD : automatiser tests, build et déploiement

Plus personne ne relance `pytest` à la main avant de merger. Un runner le fait,
sur chaque pull request, et le bouton « Merge » reste grisé tant qu'il n'est pas
vert.

## Ce que le chapitre ajoute

| Fichier | Rôle |
|----|----|
| `.github/workflows/ci.yml` | Job `test` (push + pull request), job `build-and-push` (main seulement) |
| `.dockerignore` | + `.github/` — la CI n'a rien à faire dans l'image |
| `tests/test_workflow_syntax.py` | Verrouille les six décisions du workflow dont l'oubli ne lève aucune erreur |

Le code applicatif ne bouge pas. Ce chapitre automatise l'exécution de ce qui
existait déjà depuis les Chapitres 4 à 8.

## Le workflow en deux jobs

```text
push / pull request
      │
      ▼
  [test]  checkout → setup-python → pip install -e . → dvc pull → train → pytest
      │         └→ upload-artifact: churn-model (le .pkl qui vient de passer au vert)
      │
      │ needs: test          (le build ne démarre que si les tests sont verts)
      ▼
[build-and-push]  if: github.ref == 'refs/heads/main'
      download-artifact: churn-model → login GHCR → docker build → push :<sha> et :latest
```

## Trois étapes qui ne sont pas décoratives

Un runner démarre sur un clone nu, donc vide de tout ce qui est gitignoré depuis
le Chapitre 4. Retirez-en une et voici ce que vous obtenez :

| Étape retirée | Erreur sur le runner |
|----|----|
| `pip install -e .` | `ModuleNotFoundError: No module named 'churn_predictor'` |
| `dvc pull` | `FileNotFoundError` sur `data/raw/` dans `test_data.py` |
| `python -m churn_predictor.train` | `/predict` renvoie 500, `test_app.py` échoue |

## Le modèle voyage par artefact, il n'est pas réentraîné

Le job `build-and-push` a besoin du `.pkl` lui aussi : le `COPY models/` du
Dockerfile s'arrête sinon sur `COPY failed: no source files were specified`.
Le réentraîner serait la solution naïve — et fausse : deux runners étanches,
donc rien ne garantit que le modèle construit dans le build soit celui que
`pytest` a validé (révision DVC différente, version mineure de scikit-learn
non épinglée). L'image partirait avec un binaire jamais testé, plus un run
MLflow parasite et deux minutes de CI payées pour rien.

D'où `actions/upload-artifact` à la fin de `test`, `actions/download-artifact`
au début de `build-and-push` : un seul entraînement, et le `.pkl` publié sur
GHCR est octet pour octet celui que les tests ont vu.

| Point | À savoir |
|----|----|
| Portée | Artefact visible par les jobs **du même run** ; le lire ailleurs demande le `run-id` et un token |
| Immuabilité (v4) | Deux uploads du même `name` dans un run → échec. Avec une matrice, suffixer le nom |
| Chemin | `path: models/churn_model.pkl` à l'upload, `path: models/` au download — sinon le `.pkl` atterrit à la racine |
| Confidentialité | Lisible par quiconque a accès au dépôt : un modèle, oui ; des données clients, jamais |

`actions/cache` ne remplace pas un artefact : le cache accélère (il peut
manquer), l'artefact transporte (il doit être là).

## Ce workflow ne s'exécute pas depuis ce dépôt

GitHub Actions ne lit qu'un seul emplacement : `.github/workflows/` **à la
racine du dépôt**. Ici le fichier vit dans `chapitre-10/solution/`, où il est
inerte — c'est voulu, sinon chaque chapitre déclencherait sa propre CI sur ce
dépôt de corrigés. Copié à la racine de votre projet fil rouge, il tourne.

Deux adaptations à prévoir dans votre dépôt :

- `dvc pull` suppose un remote accessible depuis un runner. Le dossier local du
  Chapitre 8 (`../churn-dvc-storage`) n'existe pas chez GitHub : il faut un remote
  Amazon S3 (`dvc remote add -d storage s3://<BUCKET>/churn` puis
  `dvc remote modify storage region eu-west-3`) et deux secrets de dépôt,
  `AWS_ACCESS_KEY_ID` et `AWS_SECRET_ACCESS_KEY`, contenant les clés d'un
  utilisateur IAM restreint à ce bucket. Tout stockage compatible S3
  (MinIO, Backblaze B2…) convient aussi : mêmes commandes,
  plus un `dvc remote modify storage endpointurl <URL>`.
- `pytest -v` sans chemin, plutôt que le `pytest tests/ -v` du livre : ici
  `pyproject.toml` déclare `testpaths`, et la commande trouve les tests dans les
  deux arborescences.

## Lancer la solution

```bash
python ../../bootstrap.py 9
cd solution
pip install -r requirements.txt && pip install -e .
python -m churn_predictor.train

pytest -v      # 39 tests (ch. 1 à 10)
```

Les huit tests du chapitre parsent le YAML, ils ne lancent aucun runner.

## Tester l'image livrée par la CI

Un package GHCR est privé par défaut : s'authentifier avec un *personal access
token* portant le seul scope `read:packages`, ou rendre le package public.

```bash
docker login ghcr.io -u <user>     # mot de passe = le token read:packages
docker pull ghcr.io/<user>/<repo>:latest
docker run -d -p 8000:8000 --name churn-ci ghcr.io/<user>/<repo>:latest
```

Sonde de vie — `curl` sous bash, `curl.exe` sous PowerShell (`curl` y est un
alias d'`Invoke-WebRequest`, qui ne connaît ni `-X`, ni `-H`, ni `-d`) :

```bash
curl http://localhost:8000/health        # curl.exe sous PowerShell
```

Prédiction, payload dans `client.json` (fourni dans `solution/`) pour éviter les
règles de *quoting* propres à chaque shell :

```bash
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d "@client.json"
```

Équivalent PowerShell natif :

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/predict" -Method Post `
  -ContentType "application/json" -InFile client.json
```

La réponse sort du `.pkl` validé par `pytest` dans le job `test`, transporté tel
quel jusqu'à l'image. Ménage : `docker rm -f churn-ci`.

## Le piège du chapitre

`on: push` sans `pull_request`. La CI tourne, elle est verte, et pourtant
rien n'a jamais bloqué un merge : elle constate après coup, comme un airbag qui
se déclenche après l'accident. `test_la_ci_se_declenche_sur_les_pull_requests`
existe précisément pour ça.

## Le piège du parseur

`yaml.safe_load` lit le `on:` d'un workflow comme le booléen `True` — la norme
YAML 1.1 traite `on`/`off` comme des booléens. La clé du dictionnaire n'est donc
pas la chaîne `"on"`, et un test naïf échoue sur un `KeyError` déroutant. La
fixture `declencheurs` du module gère les deux cas.

## Si ça ne marche pas

Les pannes rencontrées à ce TP, dans l'ordre où elles se déclarent. Le livre ne les déroule pas : elles vivent ici, à côté du code qui les provoque.

| Symptôme | Cause | Correctif |
|----|----|----|
| `ERROR: Could not find a version that satisfies the requirement numpy==...` | Le `python-version` du workflow ne correspond pas au venv qui a gelé `requirements.txt` | Recopier la sortie de `python --version` dans le workflow |
| `ModuleNotFoundError: No module named 'churn_predictor'` | Le paquet n'est pas installé sur le runner | Vérifier le `pip install -e .` du job `test` |
| `FileNotFoundError` sur `data/raw/` | `dvc pull` n'a rien ramené : secrets AWS absents ou mal nommés | *Settings → Secrets and variables → Actions* (Chapitre 9) |
| `denied: installation not allowed to Create organization package` | `build-and-push` n'a pas le droit d'écrire un package | Le bloc `permissions: packages: write` sur ce job |
| `Invoke-WebRequest : Impossible de lier le paramètre « Headers »` | `curl` est un alias de cmdlet sous Windows PowerShell 5.1 | Taper `curl.exe` |
| `422 Unprocessable Entity` sur `/predict` | Le `@` manque : cURL a envoyé le nom du fichier au lieu de son contenu | `-d "@client.json"` |
