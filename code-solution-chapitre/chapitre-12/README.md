# Chapitre 12 — Kubernetes : scaler en prod

L'API quitte le `docker run` unique. Le serveur MLflow quitte votre poste pour
le cluster, deux à six Pods identiques servent l'API, un Service répartit le
trafic, un HPA compte à votre place, et un chart Helm empaquette le tout.

## Ce que le chapitre ajoute

| Fichier | Rôle |
|----|----|
| `k8s/mlflow.yaml` | Le serveur MLflow dans le cluster : PVC, Deployment, Service `mlflow-service` |
| `k8s/configmap.yaml` | `MLFLOW_TRACKING_URI` et `MODEL_ALIAS` sortis de l'image |
| `k8s/deployment.yaml` | 2 replicas, `resources`, `readinessProbe`, `livenessProbe` |
| `k8s/service.yaml` | Adresse stable `ClusterIP`, port 80 → 8000 |
| `k8s/hpa.yaml` | 2 à 6 Pods, seuil CPU 70 % |
| `churn-api-chart/` | Les cinq manifestes — MLflow et ConfigMap compris — paramétrables par `values.yaml` |
| `src/churn_predictor/config.py` | `os.getenv` sur l'URI MLflow et l'alias du modèle |
| `tests/test_manifests.py` | 33 tests sur les manifestes et le chart, sans cluster |

## Une ConfigMap que le code ignore ne sert à rien

Depuis le Chapitre 7, `config.py` fixait l'URI de tracking en dur. La ConfigMap
serait restée décorative : la même image aurait interrogé la même base SQLite,
quel que soit l'environnement.

```python
MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI",
    f"sqlite:///{(ROOT_DIR / 'mlflow.db').as_posix()}",
)
```

La valeur locale reste en repli : rien ne casse dans les chapitres 4 à 10, et le
poste de développement continue de servir sa base SQLite.

## Prérequis : kubectl et minikube

Deux outils. `kubectl` parle à n'importe quel cluster ; `minikube` fabrique le
cluster local, dans un container Docker — le moteur du Chapitre 6 suffit, rien
d'autre à installer.

Windows (rouvrir le terminal ensuite, pour le `PATH`) :

```powershell
winget install Kubernetes.kubectl
winget install Kubernetes.minikube
```

macOS :

```bash
brew install kubectl minikube
```

Linux (Ubuntu / Debian) — binaires officiels :

```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
```

```bash
kubectl version --client
minikube version
```

## Lancer la solution

Sur Windows et macOS, Docker Desktop doit être lancé, sinon minikube s'arrête
sur `Unable to pick a default driver`. Le premier démarrage télécharge l'image
du nœud (environ 1 Go) ; comptez 2 CPU et 4 Go de RAM libres, MLflow tournant
lui aussi dans le cluster (`minikube start --driver=docker --memory=4096`).

```bash
minikube start --driver=docker
kubectl get nodes
```

```text
NAME       STATUS   ROLES           AGE   VERSION
minikube   Ready    control-plane   25s   v1.35.1
```

### Si `kubectl` refuse de parler au cluster

```text
Unable to connect to the server: tls: failed to verify certificate:
x509: certificate signed by unknown authority
```

Ni minikube ni Docker : le bouclier web d'un antivirus. Avast, AVG, Kaspersky
et ESET inspectent le trafic HTTPS en se plaçant au milieu de la connexion,
puis resignent le certificat avec leur propre autorité — jusque sur la boucle
locale. Cette autorité vit dans le magasin de certificats de Windows, que
`kubectl` ne consulte pas : il valide contre `~/.minikube/ca.crt`, voit une
signature étrangère et refuse.

```bash
# L'adresse du serveur d'API. Le port change à chaque démarrage de minikube.
kubectl config view --minify -o jsonpath="{.clusters[0].cluster.server}"

# Qui a signé le certificat servi à cette adresse ?
openssl s_client -connect 127.0.0.1:<port> < /dev/null 2>/dev/null | openssl x509 -noout -issuer
```

```text
issuer=CN=minikubeCA

issuer=O=Avast Web/Mail Shield, CN=Avast Web/Mail Shield Untrusted Root
```

Le correctif est dans l'antivirus : exclure `127.0.0.1` de l'analyse HTTPS du
bouclier web. L'adresse, jamais le port — minikube en tire un nouveau à chaque
démarrage. `--insecure-skip-tls-verify` fait taire le message sans rien
réparer : il éteint la seule vérification qui distingue votre cluster d'un
intrus. Trente secondes pour confirmer un diagnostic, jamais dans un script.

MLflow ensuite : c'est lui que la ConfigMap fait interroger aux Pods, il doit
donc exister avant eux.

```bash
kubectl apply -f k8s/mlflow.yaml
kubectl get pods -l app=mlflow
```

Le Registry est vide au démarrage — c'est un serveur neuf, sans lien avec le
`mlflow.db` de votre poste. On le remplit à travers un tunnel, `port-forward`
laissé ouvert dans un second terminal :

```bash
kubectl port-forward svc/mlflow-service 5000:5000
```

```bash
export MLFLOW_TRACKING_URI=http://localhost:5000   # $env:… en PowerShell
python -m churn_predictor.train --n-estimators 300
python -m churn_predictor.register
```

Le Secret ensuite — il n'est pas dans `k8s/`, et pour cause :

```bash
kubectl create secret generic churn-api-secret \
  --from-literal=MODEL_REGISTRY_TOKEN=changeme-en-vrai-jamais-en-clair
```

Puis les manifestes. Éditez d'abord `k8s/deployment.yaml` pour remplacer
`<user>` par votre compte GitHub :

```bash
kubectl apply -f k8s/
kubectl get pods
```

```text
NAME                         READY   STATUS    RESTARTS   AGE
churn-api-7d9f8c9b5c-abcde   1/1     Running   0          12s
churn-api-7d9f8c9b5c-fghij   1/1     Running   0          12s
```

```bash
kubectl port-forward svc/churn-api-service 8000:80
curl http://localhost:8000/health      # dans un second terminal
```

## Le chart Helm

Les cinq mêmes ressources, en une commande et sans éditer un seul YAML.
`templates/` porte `deployment.yaml`, `service.yaml`, `hpa.yaml`,
`configmap.yaml` et `mlflow.yaml` — les deux derniers ne sont pas optionnels :
sans la ConfigMap le Pod reste en `CreateContainerConfigError`, sans MLflow
l'adresse qu'elle publie ne pointe sur rien.

Le Secret, lui, reste hors du chart : `kubectl create secret` d'abord, `helm
install` ensuite. Un chart se versionne dans Git, un jeton jamais.

Le `kubectl apply -f k8s/` de la section précédente a déjà posé ces ressources,
sous les mêmes noms que ceux que la release va réclamer. Il faut donc faire le
ménage — voir « Le piège de la seconde installation » plus bas :

```bash
kubectl delete configmap churn-api-config
kubectl delete deployment churn-api mlflow
kubectl delete service churn-api-service mlflow-service
kubectl delete hpa churn-api-hpa

# mlflow-data porte la base SQLite du Registry : on l'adopte plutot que de la
# detruire, sinon le champion enregistre plus haut disparait avec le volume.
kubectl label pvc mlflow-data app.kubernetes.io/managed-by=Helm --overwrite
kubectl annotate pvc mlflow-data meta.helm.sh/release-name=churn-api meta.helm.sh/release-namespace=default --overwrite
```

```bash
helm install churn-api ./churn-api-chart --set image.tag=<sha-du-commit>
```

Vérifier le rendu avant d'appliquer quoi que ce soit :

```bash
helm lint ./churn-api-chart
helm template churn-api ./churn-api-chart | kubectl apply --dry-run=client -f -
```

`helm install --dry-run` a une limite qu'il vaut mieux connaître : sa forme par
défaut, `--dry-run=client`, rend le YAML sans jamais interroger le cluster. Elle
ne voit donc rien des ressources déjà en place. `--dry-run=server` fait valider
le rendu par l'API server et signale la collision avant l'installation.

Le chart ne fixe `replicas` que si l'autoscaling est désactivé. Sinon chaque
`helm upgrade` remettrait le compteur à sa valeur d'origine, annulant le travail
du HPA — puis l'autoscaler remonterait, en boucle.

## Tester sans cluster

Les 33 tests du chapitre lisent du YAML. Aucun `minikube` requis, donc
exécutables en CI (Chapitre 10) comme sur un poste sans Docker :

```bash
python ../../bootstrap.py 11
cd solution
pip install -r requirements.txt && pip install -e .
python -m churn_predictor.train

pytest -v      # 80 tests (ch. 1 à 12)
```

Ce qu'ils attrapent, ce sont les erreurs qui ne lèvent aucune exception :
`targetPort` qui ne correspond pas au `containerPort`, sélecteur de Service qui
ne matche aucun Pod, `requests` absentes, probes manquantes.

## Le piège du chapitre

Un Deployment sans `resources.requests` ni `readinessProbe`.

- Sans `requests`, le HPA n'a pas de dénominateur pour son pourcentage de CPU :
  il reste inerte. Aucun message d'erreur, juste un autoscaler qui ne scale
  jamais.
- Sans `readinessProbe`, le Service route du trafic vers un Pod qui vient de
  démarrer mais n'a pas fini de charger le modèle (Chapitre 5). Les premières
  requêtes échouent pendant que `kubectl get pods` affiche fièrement `Running`.

« Ça tourne » et « ça répond correctement » sont deux choses différentes. Seule
la probe fait la différence.

## Le piège de la seconde installation

Vous avez appliqué `k8s/` à la main, puis vous passez à Helm. La release
`churn-api` réclame `churn-api-config`, `churn-api`, `churn-api-service`,
`churn-api-hpa` — exactement les noms déjà présents. Helm s'arrête sur le
premier :

```text
Error: INSTALLATION FAILED: unable to continue with install: ConfigMap
"churn-api-config" in namespace "default" exists and cannot be imported into
the current release: invalid ownership metadata; label validation error:
missing key "app.kubernetes.io/managed-by": must be set to "Helm"
```

Helm reconnaît ses ressources à trois marqueurs qu'il pose lui-même : le label
`app.kubernetes.io/managed-by: Helm`, et les annotations
`meta.helm.sh/release-name` et `meta.helm.sh/release-namespace`. Un objet créé
par `kubectl apply` n'en porte aucun — pour Helm, il appartient à quelqu'un
d'autre, et il refuse d'écraser plutôt que de deviner.

Deux issues : supprimer, ou adopter en posant les marqueurs à la main. Le PVC
`mlflow-data` mérite la seconde — il porte la base SQLite du Registry, et le
détruire efface le `champion` enregistré quelques commandes plus tôt.

Le Secret échappe au problème : créé hors du chart, Helm ne cherche jamais à le
posséder. Bénéfice discret de l'avoir laissé dehors.

## Le piège de l'image privée

Un package GHCR est **privé par défaut**. Les Pods restent alors en
`ImagePullBackOff`, faute d'`imagePullSecret` — et le message ne dit pas
explicitement « votre package est privé ». Rendez-le public dans les paramètres
du package, ou déclarez un `imagePullSecret`.

## MLflow *est* le Model Registry

Pas un service de plus à installer à côté : le serveur déployé par
`k8s/mlflow.yaml` porte les deux responsabilités du Chapitre 7, le *Tracking*
(runs, paramètres, métriques) et le *Registry* (versions, alias `champion`).

Quand un Pod demande `models:/churn-api@champion` à `http://mlflow-service:5000`,
le serveur répond des métadonnées **et** un URI d'artefact — un chemin qu'il
sert lui-même, ou un `s3://…` (Chapitre 9). Le client télécharge ensuite
l'artefact à cet URI avant de le charger via `mlflow.pyfunc.load_model()`. Deux
allers-retours : un Registry joignable ne suffit pas, l'URI qu'il renvoie doit
l'être aussi.

Trois détails du manifeste ne sont pas cosmétiques :

- `replicas: 1` et `strategy: Recreate` — deux processus MLflow sur le même
  fichier SQLite le corrompent, et un volume `ReadWriteOnce` ne se monte qu'une
  fois. Un déploiement d'équipe passe à PostgreSQL + S3, et retrouve ses
  replicas.
- `sqlite:////mlflow/mlflow.db` prend quatre slashes : le quatrième est la
  racine du chemin absolu. Avec trois, la base atterrit hors du volume et
  disparaît au premier redémarrage.
- Le `PersistentVolumeClaim` sort l'historique de la couche jetable du
  container. Sans lui, `kubectl delete pod` efface toutes les expériences.

## Pourquoi aucun Secret dans `k8s/`

`kubectl create secret` crée la ressource dans le cluster, pas un fichier dans
le dépôt. Un Secret Kubernetes n'est qu'encodé en base64, pas chiffré : commité,
il est lisible par quiconque clone le dépôt, et le reste dans l'historique même
après suppression. `test_aucun_secret_en_clair_dans_les_manifestes` vérifie
qu'aucun fichier de `k8s/` ne dérive vers cette facilité. Gouvernance complète
au Chapitre 16.

## Si ça ne marche pas

Les pannes rencontrées à ce TP, dans l'ordre où elles se déclarent. Le livre ne les déroule pas : elles vivent ici, à côté du code qui les provoque.

| Symptôme | Cause | Correctif |
|----|----|----|
| `kubectl` ou `minikube` : commande introuvable | Le `PATH` du terminal date d'avant l'installation | Fermer et rouvrir le terminal |
| `Unable to pick a default driver` | Docker Desktop n'est pas lancé | Le démarrer, puis relancer `minikube start` |
| `tls: failed to verify certificate: x509: certificate signed by unknown authority` | Le bouclier web d'un antivirus inspecte le HTTPS, boucle locale comprise, et resigne le certificat de minikube | Exclure `127.0.0.1` de l'analyse HTTPS de l'antivirus — voir ci-dessous |
| Pod bloqué en `ImagePullBackOff` | Le package GHCR est privé | Le rendre public dans ses paramètres |
| Pod en `CreateContainerConfigError` | Le Deployment réclame par `envFrom` une ConfigMap ou un Secret absent | Appliquer `k8s/configmap.yaml`, recréer le Secret de l'Étape 5 |
| `helm install` : `invalid ownership metadata` | Helm refuse d'adopter une ressource créée par `kubectl apply` | Le ménage de l'Étape 10, ou l'adoption par `label` et `annotate` |
