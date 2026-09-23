# Exercice — Chapitre 9

**Starter fourni** : l'état exact laissé par `chapitre-08` — dataset sous
contrôle de DVC, pointeur commité, remote `localstorage` dans un dossier voisin.

**Objectif** : remplacer ce dossier par un bucket Amazon S3, avec un compte
correctement verrouillé et un utilisateur technique aux droits minimaux.

## À faire, sans regarder `solution/`

1. Créer un compte AWS. Dès l'activation, deux gestes avant tout le reste :
   activer le MFA sur l'utilisateur racine, et poser une alerte de budget à 1 $.
2. Créer un bucket S3 en région `eu-west-3`, blocage d'accès public laissé
   actif, versioning désactivé. Noter le nom exact.
3. Créer un utilisateur IAM `dvc-churn`, **sans** accès à la console, avec une
   politique en ligne limitée à ce seul bucket : `s3:ListBucket` sur le bucket,
   `s3:GetObject` / `s3:PutObject` / `s3:DeleteObject` sur son contenu (`/*`).
   Générer une clé d'accès.
4. `pip install "dvc[s3]"`, refiger `requirements.txt`, déclarer le remote
   `storage` et sa région, puis déposer les deux clés avec `--local`.
5. `git add .dvc/config`, commiter, `dvc push`. Vérifier dans la console S3 que
   le bucket n'est plus vide.
6. Prouver le retour : supprimer `.dvc/cache` **et** le CSV du disque, puis
   `dvc pull`.
7. Déposer `AWS_ACCESS_KEY_ID` et `AWS_SECRET_ACCESS_KEY` dans les secrets du
   dépôt GitHub — le Chapitre 10 s'en servira tel quel.

## Questions

1. Ouvrez `.dvc/config` après l'étape 4. Que contient-il exactement, et où sont
   passées les deux clés ? Quel fichier les héberge, et qui l'a gitignoré ?
2. La politique IAM comporte deux blocs `Statement`. Fusionnez-les en un seul
   avec `"Resource": "arn:aws:s3:::<bucket>"` et relancez `dvc push`. Que se
   passe-t-il, et pourquoi ?
3. Retirez la ligne `region` du remote. Relancez `dvc push`. Lisez l'erreur en
   entier : quelle région le client a-t-il tenté d'utiliser ?
4. Installez `dvc` sans l'extra `[s3]` dans un environnement neuf, puis
   `dvc push`. Notez le message exact. Que vous dit-il de l'architecture de DVC ?
5. Comparez le coût réel de ce bucket sur un an avec le prix d'un disque dur
   externe. À partir de quel volume l'arbitrage bascule-t-il ?
6. Le remote `localstorage` est toujours déclaré. Lancez
   `dvc push -r localstorage` puis `dvc push -r storage`. Les deux stockages
   contiennent-ils la même chose ? Est-ce un problème ?

## Bonus

- Reproduire le piège du chapitre dans un dépôt **privé** de test : écrire une
  fausse clé (`AKIAIOSFODNN7EXAMPLE`) dans `.dvc/config`, commiter, puis lancer
  `pytest tests/test_dvc_remote.py`. Lire le message d'échec.
- Monter le même remote sur un stockage compatible S3 auto-hébergé (MinIO en
  container). Quelle option de `dvc remote modify` faut-il en plus ?
- Activer le versioning du bucket S3 et relancer deux `dvc push` successifs.
  Qu'est-ce qui est versionné deux fois, et pourquoi est-ce inutile ici ?

## Critères de réussite

- `.dvc/config` déclare un remote `s3://` avec sa région, et **aucune** clé.
- `.dvc/config.local` contient les deux clés et n'apparaît pas dans
  `git status`.
- `dvc push` renvoie `1 file pushed`, le bucket n'est plus vide.
- Après suppression du cache et du CSV, `dvc pull` restaure le fichier à
  l'octet près.
- `pytest tests/test_dvc_remote.py` passe au vert.

## Piège de ce chapitre

`dvc remote modify` sans `--local`. La clé secrète atterrit dans un fichier
suivi par Git. Une clé publiée, même une seconde, est compromise : elle se
révoque, elle ne se rattrape pas.
