# Exercice — Chapitre 8

**Starter fourni** : l'état exact laissé par `chapitre-07` — tracking et Model
Registry MLflow en place, dataset brut simplement gitignoré, sans version
historisée.

**Objectif** : mettre le dataset sous contrôle de DVC, simuler un nouvel export
mensuel, puis revenir exactement à la version précédente.

## À faire, sans regarder `solution/`

1. `pip install dvc`, refiger `requirements.txt`, puis `dvc init`. Regarder ce
   que `git status` propose d'ajouter.
2. Créer un remote local `localstorage` pointant vers un dossier voisin de la
   racine du projet, et le déclarer par défaut.
3. Retirer la règle `data/raw/*.csv` du `.gitignore` — sinon DVC ne posera pas
   la sienne — puis `dvc add` sur le CSV. Vérifier que `data/raw/.gitignore`
   a bien été **généré**.
4. Commiter le pointeur, le `.gitignore` généré et `.dvc/config`, puis `dvc push`.
5. Écrire `scripts/simulate_new_export.py` : remplacer les 11 `TotalCharges`
   vides par `0.0`, ajouter deux clients, réécrire le CSV. Relancer `dvc add`,
   commiter, pousser.
6. Revenir à la version d'origine : `git checkout` sur l'ancien `.dvc`, puis
   `dvc checkout`.

## Questions

1. Ouvrez le fichier `.dvc` avant et après la mise à jour du dataset. Quelle
   ligne change, et pourquoi cette seule ligne suffit-elle à tout tracer ?
2. Lancez `dvc add` **sans** avoir retiré la règle `data/raw/*.csv` du
   `.gitignore`. Que manque-t-il dans la sortie ? Expliquez pourquoi.
3. Supprimez le CSV du disque (`rm data/raw/*.csv`), puis lancez `dvc checkout`.
   D'où vient le fichier restauré : du remote, ou d'ailleurs ?
4. Videz le cache (`.dvc/cache`) **et** supprimez le CSV, puis `dvc checkout`.
   Que se passe-t-il maintenant ? Quelle commande répare la situation ?
5. Combien pèse l'historique Git après cinq versions du dataset commitées via
   DVC ? Combien pèserait-il si le CSV avait été commité directement ?
6. Après avoir modifié le CSV, lancez `pytest`. Quel test du Chapitre 4 casse,
   et quel test du Chapitre 8 casse ? Que dit chacun sur ce qui a changé ?

## Bonus

- Reproduire le piège du chapitre pour de vrai : commiter un pointeur **sans**
  `dvc push`, cloner le dépôt dans un autre dossier, lancer `dvc pull`. Lire
  le message d'erreur en entier.
- Versionner aussi `models/churn_model.pkl` avec DVC. Puis argumenter : est-ce
  redondant avec le Model Registry du Chapitre 7, ou complémentaire ?
- Anticiper le Chapitre 9 : lire la documentation de `dvc remote add` pour un
  bucket S3 (`s3://mon-bucket/dvc`). Quelles commandes du TP changeraient ?
  (Réponse : aucune — seules l'URL et l'authentification bougent.)

## Critères de réussite

- `data/raw/WA_Fn-UseC_-Telco-Customer-Churn.csv.dvc` est commité, le CSV ne
  l'est pas.
- `data/raw/.gitignore` a été généré par DVC, pas écrit à la main.
- `git log -- data/raw/*.dvc` montre au moins deux versions du dataset.
- `dvc checkout` restaure la version d'origine, hash identique.
- `pytest` passe au vert sur la version d'origine.

## Piège de ce chapitre

Le `dvc push` oublié après le commit du pointeur. L'erreur ne se manifeste
jamais sur votre machine — seulement chez la personne qui clone. C'est la
définition d'un bug pénible.
