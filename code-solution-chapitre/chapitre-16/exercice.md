# Exercice — Chapitre 16

**Starter fourni** : l'état exact laissé par `chapitre-15` — monitoring en deux
couches, chaque prédiction journalisée. En clair, sans identité de l'appelant,
sans lien avec la version du modèle.

**Objectif** : rendre le système auditable après coup, et réversible en une
commande.

## À faire, sans regarder `solution/`

1. Écrire `src/churn_predictor/privacy.py` : une fonction qui transforme un
   `customerID` en empreinte stable et irréversible. Réfléchir à d'où vient le
   sel, et à ce qui doit se passer s'il est absent.
2. Ajouter `AUDIT_LOG` à `config.py`. Pourquoi un fichier distinct du journal
   du Chapitre 15 ?
3. Écrire `src/churn_predictor/audit.py` : une ligne par prédiction, répondant
   aux quatre questions de l'auditeur.
4. Brancher l'audit sur `/predict`. D'où vient l'identité de l'appelant ?
   Certainement pas du corps de la requête — pourquoi ?
5. Écrire une policy IAM qui n'autorise qu'à invoquer l'endpoint du
   Chapitre 14, rien d'autre.
6. Écrire la procédure de rollback du modèle, puis exécuter celle du
   déploiement Kubernetes.

## Questions

1. Lancez l'API sans définir `PSEUDONYM_SALT`. Que se passe-t-il ? Préférez-vous
   ce comportement à un sel par défaut ? Argumentez.
2. Changez le sel et relancez la même prédiction. L'empreinte change-t-elle ?
   Quelle conséquence pour un historique d'audit déjà accumulé ?
3. Le dataset Telco contient 7043 identifiants connus. Sans sel, combien de
   temps faut-il pour retrouver un `customerID` à partir de son SHA-256 ?
   Écrivez le script qui le prouve.
4. Un auditeur demande la liste des accès aux prédictions d'un client donné.
   Comment répondez-vous sans stocker son identifiant en clair ?
5. Le même auditeur demande la suppression de toutes les traces de ce client
   (droit à l'oubli). Que supprimez-vous exactement, et le pouvez-vous
   réellement ?
6. Coupez MLflow puis appelez `/predict`. La ligne d'audit est-elle écrite ?
   Que contient `model_version` ? Est-ce le bon compromis ?
7. Remplacez `"Resource"` par `"*"` dans la policy IAM. Quelle erreur obtenez
   -vous en l'appliquant ? (Réponse : aucune. C'est tout le problème.)
8. Faites un rollback du modèle vers une version antérieure, puis annulez ce
   rollback. Combien de versions ont été supprimées au total ?

## Bonus

- Chiffrer le journal d'audit au repos, ou l'écrire dans un stockage
  append-only (le propre d'un audit trail : personne ne doit pouvoir le
  réécrire, pas même l'équipe).
- Ajouter une politique de rétention : les lignes d'audit de plus de douze mois
  sont purgées automatiquement. Le RGPD impose-t-il une durée ?
- Faire signer chaque ligne d'audit (HMAC) pour détecter une modification
  a posteriori.
- Brancher un scan de secrets (`gitleaks`, `trufflehog`) dans la CI du
  Chapitre 10, pour qu'un sel commité bloque le merge.
- Écrire un test qui échoue si un futur développeur ajoute `customerID` au
  schéma d'entrée du Chapitre 5.

## Critères de réussite

- Aucun `customerID` en clair dans aucun fichier de `logs/`.
- La même empreinte pour le même client, une empreinte différente par
  installation.
- Chaque ligne d'audit porte l'appelant, l'horodatage UTC, l'empreinte et la
  version du modèle.
- La policy IAM ne contient qu'une action et une ressource nommée.
- `python scripts/rollback_model.py --version N` déplace l'alias sans supprimer
  aucune version.
- `kubectl rollout undo` ramène l'image précédente.
- `pytest` passe au vert.

## Piège de ce chapitre

Journaliser le `customerID` en clair « pour déboguer », en pensant le retirer
avant la production. Un identifiant qui a atterri dans un log y reste — dans les
sauvegardes, les exports, les outils tiers. La pseudonymisation est la valeur
par défaut du code, pas une étape ajoutée plus tard.
