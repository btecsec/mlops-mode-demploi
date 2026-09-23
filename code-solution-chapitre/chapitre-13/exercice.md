# Exercice — Chapitre 13

**Starter fourni** : l'état exact laissé par `chapitre-12` — manifestes
Kubernetes et chart Helm prêts, déployés sur un `minikube` créé au clic.

**Objectif** : décrire le cluster managé en Terraform, avec un state distant,
et y déployer le chart sans en changer une ligne.

## Attention aux coûts

Ce TP crée un cluster Kubernetes managé, **facturé à l'heure**. Ne sautez pas
l'étape 8 (`terraform destroy`). Si vous voulez seulement travailler la
syntaxe, `terraform plan` suffit : il ne crée rien.

## À faire, sans regarder `solution/`

1. S'authentifier auprès du cloud, lier le projet à un compte de facturation,
   activer les API Kubernetes Engine et Compute Engine, puis créer à la main le
   bucket qui accueillera le state, avec le versioning activé. Réfléchir à
   pourquoi Terraform ne peut pas créer ce bucket-là lui-même.
2. Écrire `infra/backend.tf` pointant sur ce bucket.
3. Écrire `infra/providers.tf` : provider, région, et **contraintes de version**
   sur Terraform comme sur le provider.
4. Écrire `infra/variables.tf` et `infra/main.tf` : un
   `google_container_cluster` dont rien n'est écrit en dur, et une règle
   `google_compute_firewall` qui ouvre le port du futur Service NodePort. La
   règle vise une étiquette réseau posée sur les nœuds, pas tout le réseau.
5. Écrire `infra/outputs.tf` pour récupérer l'endpoint du cluster.
6. Ajouter les règles Terraform au `.gitignore`, puis
   `terraform init`, `terraform plan -out=tfplan`, `terraform apply tfplan`.
7. Brancher `kubectl` sur le nouveau cluster, déployer le chart Helm du
   Chapitre 12 en `--set service.type=NodePort`, vérifier avec
   `kubectl get nodes`, puis joindre `/health` depuis l'extérieur du cluster —
   l'`EXTERNAL-IP` d'un nœud et le port figé.
8. `terraform destroy`, puis remettre `kubectl` sur le cluster local :
   `kubectl config delete-context gke_<projet>_europe-west1_churn-predictor-cluster`
   et `kubectl config use-context minikube`.

## Questions

1. Relancez `terraform plan` juste après un `apply` réussi, sans rien changer.
   Que dit la dernière ligne, et pourquoi ?
2. Changez `node_count` de 3 à 4 et relancez `plan`. Terraform annonce-t-il une
   création, une modification, ou une destruction suivie d'une recréation ?
3. Supprimez un nœud à la main dans la console cloud, puis relancez `plan`. Que
   propose Terraform, et sur quelle information s'appuie-t-il ?
4. Supprimez `terraform.tfvars` et relancez `plan`. Que se passe-t-il ?
   Imaginez la même chose dans un job de CI, qui n'a personne au clavier.
5. Ouvrez le state dans le bucket (`gsutil cat`). Trouvez-vous des informations
   que vous n'aimeriez pas voir dans un dépôt public ?
6. Deux personnes lancent `apply` en même temps depuis deux clones. Que fait le
   backend GCS ? Et si le state était un fichier local partagé par Git ?
7. Retirez `sensitive = true` de l'output `cluster_endpoint` et relancez
   `apply`. Que voit-on de plus dans la sortie ?
8. Supprimez la règle de pare-feu (`terraform destroy -target`), puis
   rappelez `/health` sur l'IP du nœud. `curl` répond-il par un timeout ou par
   un `connection refused` ? Qu'est-ce que cette différence vous apprend sur
   l'endroit où le paquet s'arrête ?
9. Repassez le Service en `ClusterIP` sans toucher au pare-feu, et rappelez la
   même URL. Le message de `curl` change-t-il ? Pourquoi ?
10. Retirez `--set service.nodePort=30080` et réinstallez. Relevez le port que
    Kubernetes attribue dans `kubectl get svc`. Combien de chances aviez-vous
    de tomber sur celui qu'autorise le pare-feu ?
11. Retirez `deletion_protection = false` et lancez `terraform destroy`. Que
    répond Terraform, et que se passe-t-il pendant ce temps sur la facture ?

## Bonus

- Extraire le cluster dans un module Terraform réutilisable
  (`modules/gke-cluster/`), et l'instancier deux fois : `dev` et `prod`, avec des
  tailles différentes.
- Traduire le même cluster pour AWS (`aws_eks_cluster`) ou Azure
  (`azurerm_kubernetes_cluster`). Combien de lignes changent vraiment ?
- Ajouter un job `terraform plan` à la CI du Chapitre 10, déclenché sur les pull
  requests touchant `infra/`, avec le plan posté en commentaire.
- Installer `tflint` ou `checkov` et les lancer sur `infra/`. Que remontent-ils
  que `terraform validate` laisse passer ?

## Critères de réussite

- `terraform plan` relancé sans changement affiche
  `0 to add, 0 to change, 0 to destroy`.
- Le state vit dans le bucket, pas sur votre disque.
- `git status` ne montre jamais de `.tfstate` ni de `.tfvars`.
- `kubectl get nodes` liste les nœuds du cluster créé par Terraform.
- Le chart Helm du Chapitre 12 se déploie sans modification.
- `curl http://<EXTERNAL-IP>:30080/health` répond `{"status":"ok"}` depuis
  votre poste, sans `port-forward` ouvert.
- `gcloud compute firewall-rules describe allow-churn-nodeport` montre une
  règle limitée à l'étiquette des nœuds, pas au réseau entier.
- `terraform destroy` ne laisse aucune ressource facturée derrière lui.
- `kubectl config current-context` répond `minikube`, pas le contexte GKE
  détruit — sans quoi le TP du Chapitre 15 échoue sur
  `Unable to connect to the server`.

## Piège de ce chapitre

Commiter `terraform.tfstate` pour « ne pas le perdre ». C'est le meilleur moyen
de le perdre vraiment : deux `apply` concurrents depuis deux clones s'écrasent
sans avertissement, et le fichier trimballe au passage des identifiants en clair
dans l'historique Git.
