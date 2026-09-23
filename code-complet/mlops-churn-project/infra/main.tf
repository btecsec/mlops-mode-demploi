provider "google" {
  project = var.project_id
  region  = var.region
}

# Le cluster Kubernetes manage qui accueillera le chart Helm du Chapitre 12.
# Chez AWS ce serait `aws_eks_cluster`, chez Azure `azurerm_kubernetes_cluster` :
# seuls les noms changent, la logique declarative est identique. Ce n'est pas du
# savoir jetable propre a un seul cloud.
resource "google_container_cluster" "churn_cluster" {
  name     = var.cluster_name
  location = var.region

  initial_node_count = var.node_count

  # Sans cette ligne, le provider Google refuse le `terraform destroy` de fin de
  # TP : « cannot destroy cluster because deletion_protection is set to true ».
  # Un garde-fou utile en production, une impasse ici.
  deletion_protection = false

  node_config {
    machine_type = var.machine_type
    disk_type    = var.disk_type

    # L'etiquette reseau que vise la regle de pare-feu ci-dessous. Sans elle,
    # il faudrait ouvrir le port sur toutes les machines du reseau.
    tags = [var.node_tag]
  }
}

# Un reseau GCP bloque tout le trafic entrant par defaut. Un Service NodePort
# ouvre le port cote Kubernetes, pas cote reseau : sans cette regle, la connexion
# part et n'obtient jamais de reponse — un timeout, pas un refus. Le port est
# fige (var.node_port) plutot que tire au hasard, sinon il faudrait autoriser
# les 2 768 ports de la plage pour etre sur de tomber juste.
resource "google_compute_firewall" "allow_node_port" {
  name    = "allow-churn-nodeport"
  network = var.network

  allow {
    protocol = "tcp"
    ports    = [tostring(var.node_port)]
  }

  target_tags   = [var.node_tag]
  source_ranges = var.allowed_source_ranges
}
