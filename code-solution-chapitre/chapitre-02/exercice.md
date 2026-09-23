# Exercice — Chapitre 2

**Starter fourni** : l'état laissé par `chapitre-01` — un dépôt Git et un `venv`
avec pandas, scikit-learn et jupyter. Aucune donnée.

**Objectif** : fabriquer un jeu de dix clients à la main, y construire deux
modèles triviaux, et savoir lire ce que les métriques disent vraiment de
chacun.

## À faire, sans regarder `solution/`

1. Créer `notebooks/metriques_demo.ipynb`.
2. Construire un `DataFrame` de dix clients avec trois features
   (`anciennete_mois`, `facture_mensuelle`, `contrat_mensuel`) et un label
   `churn`. Sept clients restent, trois partent.
3. Séparer `X` (les features) et `y` (le label).
4. Écrire le modèle baseline : il prédit `0` pour tout le monde, sans rien
   regarder. Calculer son accuracy et sa matrice de confusion.
5. Afficher son `classification_report`.
6. Écrire une règle métier à la main — par exemple *contrat mensuel et facture
   supérieure à 80* — et recalculer les mêmes métriques.

## Questions guidées

1. Le modèle baseline obtient 0,70 d'accuracy. D'où vient exactement ce chiffre ?
2. Dans sa matrice de confusion, pourquoi toute la colonne de droite est-elle à zéro ?
3. Que valent sa précision et son recall sur la classe `1` ? Pourquoi
   `zero_division=0` est-il nécessaire pour les afficher proprement ?
4. La règle métier fait une fausse alerte. Quelle métrique s'en trouve dégradée :
   la précision ou le recall ?
5. Un modèle affiche 100 % de recall et 20 % de précision. Que vaut sa moyenne
   arithmétique ? Son F1 ? Pourquoi cet écart est-il voulu ?
6. Sur un problème de rétention client, quelle métrique feriez-vous trancher
   par le métier avant d'entraîner quoi que ce soit — et pourquoi ?

## Critères de réussite

- Le notebook s'exécute de haut en bas sans erreur, kernel redémarré.
- Le modèle baseline sort une accuracy de 0,70 et un recall de 0,00 sur la classe `1`.
- La règle métier sort une accuracy de 0,90 et un recall de 1,00 sur la classe `1`.
- Vous savez expliquer en une phrase pourquoi le premier modèle est inutilisable
  malgré son accuracy honorable.

## Piège de ce chapitre

Évaluer un modèle sur les données qui ont servi à l'entraîner. `model.score(X_train,
y_train)` au lieu de `model.score(X_test, y_test)` : cinq caractères d'écart, et un
score qui passe de 0,78 à 0,99 sans que personne ne le remette en cause.
Toute métrique communiquée doit indiquer sur quel jeu elle a été calculée.
