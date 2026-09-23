# Exercice — Chapitre 12

**Starter fourni** : l'état exact laissé par `chapitre-11` — image publiée
automatiquement sur GHCR, modèle réentraîné chaque semaine par Airflow. Le
déploiement, lui, reste un `docker run` sur une seule machine.

**Objectif** : faire tourner MLflow et l'API sur un cluster Kubernetes, avec
plusieurs replicas pour l'API, une configuration externalisée et un autoscaling
qui réagit à la charge réelle.

## À faire, sans regarder `solution/`

1. Installer `kubectl` et `minikube` (`winget` sur Windows, `brew` sur macOS,
   binaires officiels sur Linux).
2. Démarrer un cluster local avec `minikube start --driver=docker --memory=4096`
   et vérifier avec `kubectl get nodes`.
3. Écrire `k8s/mlflow.yaml` : un `PersistentVolumeClaim`, un Deployment du
   serveur MLflow (`ghcr.io/mlflow/mlflow`, base SQLite et artefacts sur le
   volume) et un Service nommé `mlflow-service`. Appliquer, puis ouvrir
   l'interface avec `kubectl port-forward`.
4. Modifier `config.py` pour que l'application lise `MLFLOW_TRACKING_URI` dans
   son environnement, avec la configuration locale en repli. Rejouer `train.py`
   puis `register.py` contre le cluster pour y recréer l'alias `champion`, et
   pousser le commit : c'est l'image construite à partir de celui-ci que
   l'étape 6 déploiera.
5. Écrire `k8s/configmap.yaml` (URI MLflow, alias du modèle) et créer le Secret
   avec `kubectl create secret generic`.
6. Écrire `k8s/deployment.yaml` : 2 replicas, l'image publiée par votre CI **au
   SHA du commit de l'étape 4**, `envFrom` sur la ConfigMap et le Secret, les
   ressources, les deux probes sur `/health`.
7. Écrire `k8s/service.yaml` : port 80 vers `targetPort` 8000, `selector` sur le
   label du template de Pod.
8. Appliquer le tout avec `kubectl apply -f k8s/`, vérifier avec
   `kubectl port-forward` et un `curl` sur `/health`.
9. Écrire `k8s/hpa.yaml` : 2 à 6 replicas, seuil CPU à 70 %. Activer
   `metrics-server`, puis fabriquer de la charge depuis un Pod.
10. Empaqueter les cinq manifestes dans un chart Helm — `mlflow.yaml` et
    `configmap.yaml` compris, le Secret exclu — en sortant dans `values.yaml`
    tout ce qui change d'un environnement à l'autre. Avant d'installer, faire le
    ménage : les ressources posées aux étapes 5 à 9 portent déjà les noms que la
    release va réclamer, et Helm refuse d'adopter ce qu'il n'a pas créé. Adopter
    le PVC `mlflow-data` plutôt que le détruire, sinon le `champion` enregistré à
    l'étape 4 part avec le volume.

## Questions

1. Supprimez un Pod à la main (`kubectl delete pod <nom>`). Comptez les Pods
   trois secondes plus tard. Qui l'a recréé, et sur quelle base ?
2. Retirez `resources.requests` du Deployment, réappliquez, puis
   `kubectl get hpa`. Que voyez-vous dans la colonne `TARGETS` ? Le HPA
   affiche-t-il une erreur ?
3. Retirez la `readinessProbe` et redéployez. Envoyez du trafic pendant le
   démarrage : combien de requêtes échouent, et pourquoi `kubectl get pods`
   affiche-t-il quand même `Running` ?
4. Changez `targetPort` de 8000 à 8001 dans le Service. Les Pods sont-ils
   toujours `Running` ? Le `curl` passe-t-il ? Quelle commande vous permet de
   diagnostiquer sans deviner ?
5. Simulez une montée en charge avec `hey` ou `ab`. Combien de temps le HPA
   met-il à ajouter un Pod ? Et à en retirer un une fois la charge retombée ?
6. Vous déployez avec Helm alors que l'autoscaling est actif, et le chart fixe
   `replicas: 2`. Que se passe-t-il à chaque `helm upgrade` ?
7. `kubectl get secret churn-api-secret -o yaml` affiche la valeur du jeton.
   Est-elle chiffrée ? Que faut-il en conclure sur le fait de commiter un
   Secret ?
8. Lancez `helm install churn-api ./churn-api-chart` sans avoir supprimé les
   ressources posées par `kubectl apply -f k8s/`. Lisez l'erreur en entier :
   quels champs Helm réclame-t-il, et sur quelle ressource s'arrête-t-il ?
   Pourquoi le Secret n'apparaît-il jamais dans ce message ?
9. Reprenez la ressource en conflit et posez-lui à la main le label et les deux
   annotations que Helm exige. `helm install` passe-t-il ? Comparez ensuite
   `helm install --dry-run=client` et `--dry-run=server` sur un cluster où la
   collision existe encore : lequel des deux la détecte ?

## Bonus

- Ajouter un `Ingress` pour exposer l'API sur un nom de domaine plutôt que par
  `port-forward`.
- Déployer un vrai serveur MLflow dans le cluster et faire pointer la ConfigMap
  dessus. Les Pods lisent-ils le Registry sans redémarrage ?
- Ajouter un `PodDisruptionBudget` : combien de Pods peuvent être indisponibles
  pendant une mise à jour du cluster ?
- Brancher `helm lint` et `kubectl apply --dry-run=client` dans la CI du
  Chapitre 10, pour qu'un manifeste cassé bloque le merge.
- Passer le HPA sur une métrique custom (nombre de requêtes par seconde) plutôt
  que sur le CPU. Le Chapitre 15 fournit la métrique.

## Critères de réussite

- `kubectl get pods` affiche au moins deux Pods `1/1 Running`.
- Supprimer un Pod le fait recréer automatiquement.
- `curl /health` répond via le Service, pas via l'IP d'un Pod.
- `kubectl get hpa` affiche un pourcentage de CPU, pas `<unknown>`.
- `helm install` déploie l'ensemble en une commande, `helm lint` ne renvoie
  aucune erreur.
- `helm list` affiche une release `deployed`, et `kubectl get pvc mlflow-data`
  un volume que Helm a adopté — le Registry a survécu au passage sous chart.
- `pytest` passe au vert, sans cluster démarré.

## Piège de ce chapitre

Un Deployment sans `resources.requests` ni `readinessProbe`. Aucun des deux
oublis ne produit d'erreur : le HPA reste simplement inerte, et le trafic part
vers des Pods qui ne sont pas encore prêts à le servir.
