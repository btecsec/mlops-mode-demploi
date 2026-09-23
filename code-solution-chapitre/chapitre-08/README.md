# Chapitre 8 — DVC : versionner les données

Le CSV brut sort du `.gitignore` manuel et entre sous contrôle de DVC. Ce qui
part dans Git : un pointeur de quatre lignes. Ce qui part dans le remote : les
977 Ko de données réelles.

## Ce que le chapitre ajoute

| Fichier | Rôle |
|----|----|
| `.dvc/config` | Déclare le remote par défaut `localstorage` (un dossier voisin) |
| `.dvcignore` | Ce que DVC ne doit pas scruter — l'équivalent du `.gitignore`, côté données |
| `data/raw/*.csv.dvc` | Le pointeur : hash MD5, taille, nom du fichier suivi |
| `data/raw/.gitignore` | **Généré par DVC**, ciblé sur le seul fichier suivi |
| `solution/.gitignore` | La règle manuelle `data/raw/*.csv` du Chapitre 4 disparaît |
| `scripts/simulate_new_export.py` | Simule l'export mensuel du service client (corrections + 2 clients) |
| `tests/test_dvc_pointer.py` | Le pointeur existe, son hash correspond au fichier, un remote est déclaré |

Le code du modèle ne bouge pas d'une ligne. Ce chapitre versionne les données,
pas le programme — c'est précisément la brique qui manquait au Chapitre 7 pour
répondre à « quelles données ont produit ce modèle ? ».

## Où vit le remote

Le livre déclare `../churn-dvc-storage` : un dossier voisin de la racine du
projet. Ici, la racine du projet est `chapitre-08/solution/`, donc le vestiaire
est `chapitre-08/churn-dvc-storage/` — gitignoré, comme il se doit. Un vrai
projet pointerait vers S3, GCS ou Azure Blob : seule l'URL change,
pas les commandes.

## Lancer la solution

```bash
python ../../bootstrap.py 8
cd solution
pip install -r requirements.txt && pip install -e .

dvc status
```

```text
Data and pipelines are up to date.
```

Ce message vaut vérification : le hash inscrit dans le pointeur commité
correspond bien, octet pour octet, au CSV installé par `bootstrap.py`.

## Pousser les données dans le vestiaire

Un dépôt fraîchement cloné n'a pas de remote peuplé — le stockage local est
gitignoré, il ne voyage pas avec le code. On le remplit une fois :

```bash
dvc push
```

```text
1 file pushed
```

À partir de là, `dvc pull` et `dvc checkout` fonctionnent, y compris après avoir
supprimé le CSV du disque.

## Rejouer la mise à jour du dataset

Le TP du chapitre ne s'arrête pas au premier `dvc add` : il simule un nouvel
export, le versionne, puis revient en arrière. Les commandes, dans l'ordre :

```bash
python scripts/simulate_new_export.py
```

```text
7045 lignes écrites
```

```bash
dvc status                      # le hash local ne correspond plus au pointeur
dvc add data/raw/WA_Fn-UseC_-Telco-Customer-Churn.csv
git add data/raw/*.dvc
git commit -m "data: nouvel export mensuel (TotalCharges corrigés)"
dvc push
```

Puis le retour en arrière, celui qui répond à l'auditeur :

```bash
git log --oneline -- data/raw/*.dvc
git checkout <hash-du-commit-precedent> -- data/raw/*.dvc
dvc checkout --force
```

```text
M       data/raw/WA_Fn-UseC_-Telco-Customer-Churn.csv
```

Le fichier local retrouve exactement les 7043 lignes d'origine — même hash,
mêmes octets. `--force` est nécessaire dès que le fichier de travail contient
des modifications non enregistrées : DVC refuse d'écraser sans confirmation.

`solution/` est livré sur la **première** version du dataset, celle que
`bootstrap.py` installe. C'est ce qui garde `dvc status` propre à la sortie du
clone.

## Lancer les tests

```bash
pytest -v      # 26 tests (ch. 1 à 5)
```

Les cinq tests du chapitre tournent sans DVC installé : ils relisent le pointeur
et recalculent le MD5 eux-mêmes. Le hash n'est pas une notion réservée à l'outil.

## Le piège du chapitre

`git commit` sur le pointeur, puis passer à autre chose sans `dvc push`. Le
ticket de vestiaire circule, le manteau n'a jamais été déposé. Le collègue qui
récupère le dépôt obtient :

```text
$ dvc pull
ERROR: failed to pull data from the cloud - Checkout failed for following targets:
data/raw/WA_Fn-UseC_-Telco-Customer-Churn.csv
```

L'erreur apparaît chez lui, pas chez vous — c'est ce qui la rend pénible à
diagnostiquer. Réflexe à ancrer : `dvc push` suit un commit de `.dvc` comme
`git push` suit un commit de code.

## Le détail qui bloque tout le monde

Tant que le `.gitignore` du Chapitre 4 contient `data/raw/*.csv`, `dvc add`
considère le travail d'exclusion déjà fait et ne génère **pas**
`data/raw/.gitignore`. Symptôme : la sortie de `dvc add` ne mentionne que le
fichier `.dvc`. Il faut retirer la règle manuelle d'abord, relancer ensuite.

## Si ça ne marche pas

Les pannes rencontrées à ce TP, dans l'ordre où elles se déclarent. Le livre ne les déroule pas : elles vivent ici, à côté du code qui les provoque.

| Symptôme | Cause | Correctif |
|----|----|----|
| `dvc add` ne mentionne pas `data/raw/.gitignore` | La règle `data/raw/*.csv` du Chapitre 4 est encore dans le `.gitignore` : DVC croit le travail fait | La retirer, puis relancer `dvc add` |
| `tail : Le terme «tail» n'est pas reconnu` | `tail` n'existe pas sous PowerShell | `Get-Content <fichier> -Tail 2` |
| Sur un autre poste, `dvc pull` : `No remote provided` | `.dvc/config` n'a pas été commité | `git add .dvc/config` |
| Le pointeur est dans Git, mais les données manquent au clone suivant | `dvc push` oublié après le commit | C'est le piège classique de ce chapitre |
| `dvc checkout` ne change rien | Le `.dvc` n'a pas été ramené en arrière | Vérifier `git status` sur `data/raw/*.dvc` avant de relancer |
