# Pas de valeur par defaut : un identifiant de projet cloud n'a rien a faire en
# dur dans un fichier partage. Sans valeur fournie, Terraform s'interrompt et
# attend une saisie au clavier — ce qui bloque une CI aussi surement qu'un TP.
variable "project_id" {
  type        = string
  description = "Identifiant du projet GCP. A fournir via terraform.tfvars, non versionne."
}

variable "region" {
  type        = string
  description = "Region du cluster."
  default     = "europe-west1"
}

# Un cluster regional replique ce nombre dans CHAQUE zone de la region : 1 ici
# donne 3 noeuds, pas 1. Monter a 3 en demande 9, et le quota CPU par defaut
# d'un nouveau projet GCP ne suit pas.
variable "node_count" {
  type        = number
  description = "Nombre de noeuds par zone."
  default     = 1
}

variable "cluster_name" {
  type        = string
  description = "Nom du cluster Kubernetes manage."
  default     = "churn-predictor-cluster"
}

variable "machine_type" {
  type        = string
  description = "Type de machine des noeuds."
  default     = "e2-small"
}

# Le SSD est le defaut de GKE, et le quota SSD_TOTAL_GB d'un projet neuf est vite
# atteint. Le disque standard suffit largement pour ce TP.
variable "disk_type" {
  type        = string
  description = "Type de disque des noeuds."
  default     = "pd-standard"
}

variable "network" {
  type        = string
  description = "Reseau VPC accueillant le cluster."
  default     = "default"
}

# L'etiquette posee sur les noeuds, et visee par la regle de pare-feu : la regle
# ne s'applique donc qu'aux machines du cluster, pas a tout le reseau.
variable "node_tag" {
  type        = string
  description = "Etiquette reseau des noeuds du cluster."
  default     = "churn-node"
}

# Fige, pas tire au hasard : la regle de pare-feu doit autoriser a l'avance le
# port exact que le Service ouvrira. A garder aligne avec `service.nodePort` du
# chart Helm.
variable "node_port" {
  type        = number
  description = "Port NodePort expose sur les noeuds."
  default     = 30080
}

# 0.0.0.0/0 ouvre le port a l'Internet entier. Tolerable le temps d'un TP sur une
# API sans donnees reelles, jamais au-dela : votre IP publique se lit avec
# `curl ifconfig.me`, et se met ici sous la forme ["203.0.113.7/32"].
variable "allowed_source_ranges" {
  type        = list(string)
  description = "Plages autorisees a joindre le NodePort."
  default     = ["0.0.0.0/0"]
}
