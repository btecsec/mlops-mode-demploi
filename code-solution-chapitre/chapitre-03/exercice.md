# Exercice — Chapitre 3

**Starter fourni** : l'état laissé par `chapitre-02` — un dépôt Git, un `venv`,
et le vocabulaire des métriques. Aucune donnée réelle encore.

**Objectif** : ouvrir le dataset du fil rouge, comprendre ce que contient
chaque famille de colonnes, entraîner un premier modèle et mesurer honnêtement
ce qu'il vaut.

## À faire, sans regarder `solution/`

1. Télécharger *Telco Customer Churn* depuis Kaggle et le déposer dans `data/`.
2. Créer `exploration.ipynb` à la racine du projet — oui, à la racine, et oui
   c'est sale.
3. Afficher `df.shape`, la répartition de `Churn`, et `df.dtypes.value_counts()`.
4. Repérer et corriger le problème de type sur `TotalCharges`.
5. Croiser le taux de churn avec `Contract`, puis avec des tranches de `tenure`.
6. Séparer `X` et `y`, découper en train / test avec `random_state=42`.
7. Calculer le baseline sur le jeu de test **avant** d'entraîner quoi que ce soit.
8. Construire un `Pipeline` `OneHotEncoder` + `RandomForestClassifier`, l'entraîner,
   afficher `classification_report` **et** l'accuracy sur le train.
9. Sauvegarder le pipeline avec `joblib.dump`.

## Questions guidées

1. Combien de colonnes sont du texte, et pourquoi est-ce un problème pour scikit-learn ?
2. Pourquoi `customerID` doit-il sortir de `X` ? Que se passe-t-il concrètement si
   on l'y laisse ? *(indice : `df.nunique()`, puis comptez les colonnes après encodage)*
3. Quelles sont les onze lignes problématiques de `TotalCharges`, et qu'ont-elles
   en commun ? Pourquoi `fillna(0)` est-il un choix métier défendable ici ?
4. Le taux de churn passe de 42,7 % à 2,8 % entre deux types de contrat. Qu'est-ce
   que ça dit au métier, indépendamment de tout modèle ?
5. Le modèle affiche 0,9986 en train et 0,7913 en test. Quel est le diagnostic ?
6. Sur 373 départs réels, le modèle en détecte 173. Est-ce acceptable pour une
   campagne de rétention ? Quelle métrique faudrait-il chercher à améliorer en priorité ?
7. Pourquoi sauvegarder le `Pipeline` entier plutôt que le seul `RandomForestClassifier` ?
8. Listez trois raisons pour lesquelles ce notebook ne peut pas partir en production
   tel quel.

## Critères de réussite

- Le notebook s'exécute de haut en bas sans erreur, kernel redémarré.
- `df.shape` renvoie `(7043, 21)`.
- Le baseline sur le jeu de test tombe à 0,7353.
- L'accuracy de test dépasse le baseline (autour de 0,79).
- Un fichier `model.pkl` est produit — et **n'est pas** commité.
- Vous savez expliquer pourquoi un recall de 0,46 est le vrai résultat du chapitre.

## Piège de ce chapitre

Oublier de retirer `customerID` de `X`. Le code ne plante pas : `OneHotEncoder`
fabrique consciencieusement 7043 colonnes binaires, une par client.
L'entraînement devient dix fois plus lent, le `.pkl` gonfle, et le modèle apprend
à reconnaître des identifiants au lieu de comportements — donc devient inutile
sur des clients jamais vus.

**Toute colonne dont chaque valeur est unique est un identifiant, jamais une feature.**
