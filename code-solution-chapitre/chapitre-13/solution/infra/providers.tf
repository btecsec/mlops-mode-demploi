# Versions épinglées : sans contrainte, un `terraform init` lancé six mois plus
# tard récupère une version majeure du provider aux ressources renommées, et le
# plan diverge sans qu'une seule ligne du code ait bougé.
terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
