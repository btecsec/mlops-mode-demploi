# Exercice — Chapitre 15

**Starter fourni** : l'état exact laissé par `chapitre-14` — modèle servi par la
stack maison et par un endpoint managé. Aucune vérification n'existe pour savoir
si les données reçues ressemblent encore à celles de l'entraînement.

**Objectif** : ajouter les deux couches de monitoring, puis brancher la
deuxième sur le ré-entraînement.

## À faire, sans regarder `solution/`

1. Instrumenter l'API pour exposer `/metrics`, puis lancer Prometheus et
   Grafana avec un `docker-compose.yml`. Envoyer ensuite une soixantaine de
   prédictions : sans trafic, Grafana n'a aucune série à tracer.
2. Ajouter `PREDICTIONS_LOG` à `config.py`. Réfléchir à pourquoi le chemin doit
   être ancré sur `ROOT_DIR` et pas relatif au dossier courant.
3. Écrire `log_prediction()` **et** l'appeler depuis `/predict`. Une fonction
   jamais appelée ne journalise rien.
4. Écrire `monitoring/check_drift.py` : charger la baseline, charger le journal,
   comparer avec `DataDriftPreset`, retourner la part de colonnes dérivées.
5. Rendre `monitoring/` importable par le DAG.
6. Ajouter une tâche de branchement au DAG du Chapitre 11 : ré-entraîner
   seulement si le drift dépasse le seuil.
7. Alimenter le journal avec 200 lignes du dataset, puis mesurer.

## Questions

1. Lancez `check_drift.py` avant d'avoir appelé `/predict` une seule fois. Quel
   message obtenez-vous, et pourquoi vaut-il mieux ça qu'un `FileNotFoundError` ?
2. Le premier résultat annonce 0 % de dérive. Est-ce rassurant, ou juste
   attendu ? Sur quel dataset le trafic de test a-t-il été tiré ?
3. Simulez un vrai drift : multipliez `MonthlyCharges` par 3 et forcez
   `Contract` à `Two year` sur les 200 lignes envoyées. Quel pourcentage
   obtenez-vous ? Le DAG déclenche-t-il le ré-entraînement ?
4. Retirez le `pd.to_numeric` sur `TotalCharges` dans le chargement de la
   baseline. Le taux de dérive change-t-il ? Pourquoi, alors que les données
   sont les mêmes ?
5. Oubliez le `__init__.py` de `monitoring/` et déclenchez le DAG. Quelle
   erreur, et à quel chapitre l'aviez-vous déjà croisée ?
6. Coupez l'API pendant que Prometheus tourne. Que voit-on dans Grafana ? Et si
   à la place le modèle se met à répondre systématiquement `churn: false` —
   Grafana le voit-il ?
7. `DRIFT_THRESHOLD` vaut 0.3. Que se passerait-il avec 0.05 ? Avec 0.9 ?
   Comment choisiriez-vous cette valeur sur un vrai service ?

## Bonus

- Construire un dashboard Grafana avec trois panneaux : requêtes/seconde,
  latence p95, taux d'erreur 5xx. L'exporter en JSON et le versionner.
- Ajouter une métrique Prometheus **métier** : la distribution des probabilités
  prédites. Un modèle qui bascule d'un coup vers 0 se voit alors dans la
  Couche 1 aussi.
- Sauvegarder le rapport Evidently complet en HTML — `save_html()` s'appelle sur
  l'instantané rendu par `run()`, pas sur le `Report` — et le publier en artefact
  du DAG. Le pourcentage seul ne dit pas *quelle* colonne a dérivé.
- Faire tourner `check_drift.py` sur une fenêtre glissante (les 7 derniers
  jours du journal) plutôt que sur tout l'historique. Pourquoi est-ce important
  au bout de six mois de production ?
- Alerter sur Slack quand le seuil est franchi, plutôt que d'attendre le
  prochain passage du DAG.

## Critères de réussite

- `GET /metrics` répond au format Prometheus, Grafana affiche des données.
- Un panneau trace `rate(http_requests_total{handler="/predict"}[1m])` et la
  courbe monte pendant la boucle de trafic, pas avant.
- Chaque appel à `/predict` ajoute exactement une ligne au journal, l'en-tête
  n'est écrit qu'une fois.
- `check_drift.py` retourne 0 % sur du trafic tiré de la baseline.
- Un drift artificiel dépasse le seuil et déclenche `train_challenger`.
- Un drift sous le seuil emprunte la branche `skip_retrain`, visible dans
  l'interface.
- `pytest` passe au vert.

## Piège de ce chapitre

Se contenter de la Couche 1. Latence excellente, zéro erreur 500, disponibilité
à 100 % — et un modèle qui se trompe depuis trois jours. Le dashboard mesure la
disponibilité, jamais la justesse.
