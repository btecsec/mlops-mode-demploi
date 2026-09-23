# Chapitre 13 — Terraform : provisionner l'infra en Infrastructure as Code

Le cluster ne se crée plus au clic dans une console. Il est décrit dans cinq
fichiers texte, versionnés, relisibles en revue de code, et rejouables ailleurs
à l'identique.

## Ce que le chapitre ajoute

| Fichier | Rôle |
|----|----|
| `infra/backend.tf` | State dans un bucket GCS, partagé et verrouillé |
| `infra/providers.tf` | Provider Google épinglé, `required_version` |
| `infra/variables.tf` | `project_id` sans défaut, région, taille du cluster, port et plages autorisées |
| `infra/main.tf` | `google_container_cluster` + la règle de pare-feu du NodePort |
| `infra/outputs.tf` | Endpoint (marqué `sensitive`) et nom du cluster |
| `infra/terraform.tfvars.example` | Le gabarit à copier — le vrai fichier est gitignoré |
| `.gitignore` | `*.tfstate`, `*.tfvars`, `infra/.terraform/` |
| `tests/test_terraform_validate.py` | `terraform fmt` + 16 assertions sur le HCL |

Le chart Helm du Chapitre 12 ne change pas d'une ligne : il ignore totalement que
le cluster vient d'être créé par Terraform plutôt qu'à la main. C'est
exactement l'intérêt de séparer infrastructure et applicatif.

## L'ordre compte : le bucket avant tout

Terraform ne crée jamais le bucket de son propre backend — il lui faudrait y
écrire son état avant d'avoir un endroit où l'écrire. C'est le seul élément
d'infrastructure créé à la main de tout le chapitre :

```bash
gcloud auth application-default login
gcloud config set project <votre-projet-gcp>

gsutil mb -l europe-west1 gs://churn-predictor-tfstate
gsutil versioning set on gs://churn-predictor-tfstate
```

Le versioning est l'assurance-vie : un `apply` malheureux qui corrompt le state
se répare en restaurant la version précédente.

## Lancer la solution

```bash
cp infra/terraform.tfvars.example infra/terraform.tfvars
# renseigner project_id dans le fichier copié
```

```bash
cd infra
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

```text
Plan: 1 to add, 0 to change, 0 to destroy.
```

Rien n'est créé après `plan`. `apply tfplan` applique le plan exact déjà relu —
aucune divergence possible entre ce qui a été validé et ce qui s'exécute.

Puis brancher `kubectl` et déployer le chart du Chapitre 12 :

```bash
gcloud container clusters get-credentials churn-predictor-cluster --region europe-west1
kubectl get nodes

helm install churn-api ./churn-api-chart --set service.type=NodePort --set service.nodePort=30080
```

## Deux ressources, pas une

Le chapitre crée le cluster **et** la porte pour y entrer. C'est l'erreur la
plus fréquente sur un premier cluster managé : on expose correctement l'API côté
Kubernetes, et on oublie que le réseau du cloud, lui, n'a rien autorisé.

Un Service `NodePort` ouvre le même port sur toutes les machines du cluster.
Deux verrous sont donc à lever, et rater le second ne produit aucun message
d'erreur — juste un `curl` qui ne revient pas :

| Verrou | Qui l'ouvre | Ce qu'on voit s'il reste fermé |
|----|----|----|
| Le port sur le nœud | Kubernetes (`service.type=NodePort`) | `connection refused`, immédiat |
| Le trafic entrant | Terraform (`google_compute_firewall`) | Un timeout, sans message |

Le port n'est pas laissé au hasard : `var.node_port` côté Terraform et
`service.nodePort` côté chart valent tous deux `30080`. Sans ce réglage,
Kubernetes en tire un au hasard entre 30000 et 32767, et il faudrait ouvrir les
2 768 ports pour être sûr de tomber juste. `test_le_nodeport_du_chart_et_du_pare_feu_sont_alignes`
verrouille cette correspondance : c'est l'incohérence que ni Terraform ni Helm
ne peuvent voir seuls.

`allowed_source_ranges` vaut `["0.0.0.0/0"]` : le port est ouvert à l'Internet
entier. Tolérable le temps d'un TP sur une API sans données réelles, jamais
au-delà. Votre IP publique se lit avec `curl ifconfig.me`, et se met sous la
forme `["203.0.113.7/32"]`.

## Débuguer quand rien ne répond

Descendre les couches une par une, en s'arrêtant à la première qui ment :

```bash
kubectl get pods
kubectl get endpoints churn-api-service
kubectl run debug --rm -i --restart=Never --image=curlimages/curl:8.11.1 -- curl -s http://churn-api-service/health
kubectl get nodes -o wide
gcloud compute firewall-rules describe allow-churn-nodeport
```

La troisième commande est la charnière. Si elle renvoie `{"status":"ok"}`,
l'application et le Service sont hors de cause : le problème est réseau. Si elle
échoue, inutile de toucher au pare-feu.

La distinction la plus utile vient de `curl` lui-même. Un **timeout** signifie
que le paquet a été jeté en silence — pare-feu, ou mauvaise IP. Un
**`connection refused`**, immédiat, signifie l'inverse : le paquet est arrivé,
mais rien n'écoute sur ce port — mauvais nodePort, ou Service resté en
`ClusterIP`.

## Détruire, ce n'est pas optionnel

```bash
terraform destroy
```

Un cluster GKE oublié facture chaque heure qui passe. `terraform destroy`
supprime exactement ce que Terraform a créé — jamais plus, jamais moins.

À condition que `deletion_protection = false` soit dans `main.tf` : depuis le
provider Google 6, la valeur par défaut est `true` et `destroy` refuse de
partir sur un message limpide (« cannot destroy cluster because
deletion_protection is set to true ») pendant que le cluster continue de
facturer.

Terraform ne touche pas au kubeconfig de votre poste. Le contexte écrit par
`gcloud container clusters get-credentials` y reste, et il reste courant : tout
`kubectl` lancé ensuite vise l'IP d'un serveur d'API détruit et finit en
`Unable to connect to the server: dial tcp <ip>:443`. Le symptôme ressemble à
une panne réseau ; c'est une cible qui n'existe plus.

```bash
# Le nom exact du contexte : gke_<votre-projet>_<région>_<cluster>.
kubectl config get-contexts

kubectl config delete-context gke_<votre-projet>_europe-west1_churn-predictor-cluster
kubectl config use-context minikube
```

`delete-context` ne retire que le contexte ; les entrées `cluster` et `user`
du même nom survivent, sans effet, et se suppriment par
`kubectl config delete-cluster` et `kubectl config delete-user`. Les chapitres
suivants repartent du cluster local du Chapitre 12.

## Lancer les tests

```bash
pytest -v      # 81 tests (ch. 1 à 9)
```

Les 17 tests du chapitre ne créent aucune ressource et n'appellent aucun cloud.
`terraform fmt -check` tourne quand Terraform est installé, et se met en skip
sinon.

`terraform validate`, en revanche, n'est **pas** dans la suite : il exige un
`terraform init` préalable qui télécharge le provider Google, plusieurs
centaines de mégaoctets. À lancer une fois, à la main :

```bash
cd infra
terraform init -backend=false      # pas besoin du bucket pour valider la syntaxe
terraform validate
```

## Ce que les tests verrouillent vraiment

Ce ne sont pas des fautes de syntaxe — Terraform les attrape déjà. Ce sont les
décisions coûteuses :

- un backend distant, pas un `terraform.tfstate` sur un disque
- `project_id` sans valeur par défaut, donc jamais l'identifiant d'un autre
- un provider épinglé (`~> 6.0`), donc un plan qui ne dérive pas tout seul
- un endpoint marqué `sensitive`, donc absent des logs d'un apply en CI

## Le piège du chapitre

Commiter `terraform.tfstate` « pour ne pas le perdre ». Deux problèmes cumulés :

- le fichier contient parfois des données sensibles en clair (IP, identifiants
  de ressources) ;
- deux personnes qui appliquent depuis deux clones différents écrasent l'état
  l'une de l'autre, sans le moindre avertissement.

Le state n'est pas du code : c'est la mémoire de l'infrastructure. Sa place est
dans un backend distant verrouillé, pas dans Git.

## Le piège de la variable manquante

`project_id` n'a pas de valeur par défaut, volontairement. Sans
`terraform.tfvars`, Terraform s'interrompt sur `var.project_id: Enter a value:`
et attend une saisie au clavier — ce qui bloque un TP mais surtout un job de CI,
qui n'a personne pour taper.

## Si ça ne marche pas

Les pannes rencontrées à ce TP, dans l'ordre où elles se déclarent. Le livre ne les déroule pas : elles vivent ici, à côté du code qui les provoque.

| Symptôme | Cause | Où creuser |
|----|----|----|
| Pod en `Pending` | Pas assez de CPU sur les nœuds, ou quota GCP atteint | `kubectl describe pod <nom>` |
| Pod en `CreateContainerConfigError` | ConfigMap ou Secret absent du cluster | `kubectl describe pod <nom>` |
| Pod en `CrashLoopBackOff` | L'API démarre puis meurt | `kubectl logs <nom> --previous` |
| `port-forward` marche, l'IP du nœud non | Couche réseau : pare-feu absent, ou étiquette `churn-node` non posée | `gcloud compute firewall-rules list` |
| `destroy` : *cannot destroy cluster because deletion_protection is set to true* | Le garde-fou du provider Google 6, laissé à sa valeur par défaut | La ligne `deletion_protection = false` de l'Étape 3 |
| `Unable to connect to the server: dial tcp <ip>:443` | Le contexte kubectl pointe sur un cluster détruit | Le ménage du kubeconfig, Étape 8 |
