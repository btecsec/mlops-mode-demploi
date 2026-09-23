# Chapitre 9 — Le cloud pour vos données : compte AWS et bucket S3

Le remote DVC du Chapitre 8 était un dossier voisin, sur un seul disque. Il
devient ici un bucket Amazon S3 : durable, et surtout joignable depuis une
machine qui n'est pas la vôtre — ce dont la CI du Chapitre 10 a besoin dès sa
première ligne.

## Ce que le chapitre ajoute

| Fichier | Rôle |
|----|----|
| `.dvc/config` | Déclare le remote `storage` (`s3://…`) et sa région, à côté du remote local |
| `.dvc/config.local` | **Jamais commité** : les deux clés d'accès y vivent, `dvc init` l'a déjà gitignoré |
| `requirements.txt` | `dvc` devient `dvc[s3]` — le client S3 arrive avec l'extra |
| `tests/test_dvc_remote.py` | Un remote S3 est déclaré, avec sa région, et aucune clé n'a fui dans un fichier suivi |

Le code du modèle ne bouge toujours pas. Ce chapitre déplace le stockage des
données, pas le programme.

## Le bucket est à vous, pas à ce dépôt

`.dvc/config` porte volontairement une URL bidon :

```ini
['remote "storage"']
    url = s3://churn-dvc-a-remplacer/churn
    region = eu-west-3
```

Un nom de bucket S3 est unique à l'échelle mondiale : celui du livre ne peut pas
être le vôtre. Après avoir créé le vôtre (TP, étape 3), remplacez l'URL et
déposez vos clés **hors de Git** :

```bash
cd solution
dvc remote modify storage url s3://<votre-bucket>/churn
dvc remote modify --local storage access_key_id <access-key-id>
dvc remote modify --local storage secret_access_key <secret-access-key>
dvc push -r storage
```

```text
1 file pushed
```

Le `--local` écrit dans `.dvc/config.local`, ignoré par Git. Sans lui, la clé
part en clair au premier `git push` — c'est le piège du chapitre, et
`tests/test_dvc_remote.py` le vérifie à chaque exécution.

## Pourquoi le remote par défaut reste `localstorage`

Le livre fait de S3 le remote **par défaut** (`dvc remote add -d`). Ce dépôt,
lui, garde `localstorage` par défaut pour une raison pratique : les corrigés
doivent tourner sans compte AWS, hors ligne, y compris dans un train. Les deux
remotes sont déclarés côte à côte ; `-r storage` choisit explicitement le bucket.

Pour coller exactement au livre une fois votre bucket créé :

```bash
dvc remote default storage
```

## Lancer la solution

```bash
python ../../bootstrap.py 9
cd solution
pip install -r requirements.txt && pip install -e .

dvc status
```

```text
Data and pipelines are up to date.
```

## Lancer les tests

```bash
pytest -v      # 31 tests (ch. 1 à 9)
```

Les cinq tests du chapitre ne touchent pas au réseau : ils relisent
`.dvc/config`, `.dvc/.gitignore` et `requirements.txt`. Aucun compte AWS n'est
nécessaire pour les faire passer — et aucun euro dépensé.

## Le piège du chapitre

`dvc remote modify storage secret_access_key <clé>` **sans** `--local`. Tout
fonctionne, et la clé est maintenant dans `.dvc/config`, un fichier suivi par
Git. Sur un dépôt public, des robots scannent les nouveaux commits en continu :
le délai entre la publication d'une clé AWS et sa première utilisation par un
tiers se compte en minutes.

Le réflexe, avant chaque commit touchant à DVC :

```bash
git diff --cached .dvc/config
```

Si la clé est déjà partie, réécrire l'historique ne suffit pas : il faut la
désactiver puis la supprimer dans IAM, et en générer une nouvelle.

## Le détail qui bloque tout le monde

`pip install dvc` sans l'extra, puis `dvc push` sur un remote `s3://` :

```text
ERROR: URL 's3://mon-bucket/churn' is supported but requires these missing dependencies: ['dvc-s3']
```

Le message est explicite, mais il arrive tard — après la création du compte, du
bucket et de l'utilisateur IAM, au moment précis où on croyait avoir fini.
D'où `dvc[s3]` épinglé dans `requirements.txt`, et un test qui le vérifie.

## Si ça ne marche pas

Les pannes rencontrées à ce TP, dans l'ordre où elles se déclarent. Le livre ne les déroule pas : elles vivent ici, à côté du code qui les provoque.

| Symptôme | Cause | Correctif |
|----|----|----|
| `zsh: no matches found: dvc[s3]` | Les crochets nus sont pris pour un motif de fichiers | Les guillemets : `pip install "dvc[s3]"` |
| *Bucket name already exists* à la création | Le nom d'un bucket est unique à l'échelle mondiale | Suffixer avec votre identifiant |
| `dvc push` : `AccessDenied` ou `Forbidden` | La politique IAM ne couvre pas l'action, ou le nom du bucket est faux dans l'ARN | Relire les deux blocs `Statement` de l'Étape 4 |
| `dvc push` : `NoCredentialsError` | Les deux `dvc remote modify --local` n'ont pas été passés | Les rejouer, puis vérifier `.dvc/config.local` |
| `dvc push` : `EndpointConnectionError` | La région du remote ne correspond pas à celle du bucket | `dvc remote modify storage region <la-bonne>` |
| Au Chapitre 10, `dvc pull` : `Unable to locate credentials` | Les secrets GitHub sont absents ou mal nommés | Les recréer avec les noms exacts de l'Étape 7 |
