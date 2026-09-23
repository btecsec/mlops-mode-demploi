# Où Terraform range sa mémoire. Le bucket doit exister AVANT le premier
# `terraform init` : Terraform ne crée jamais le bucket de son propre backend —
# il lui faudrait y écrire son état avant d'avoir un endroit où l'écrire.
#
#   gsutil mb -l europe-west1 gs://churn-predictor-tfstate
#   gsutil versioning set on gs://churn-predictor-tfstate
#
# Le versioning est l'assurance-vie : un apply malheureux qui corrompt le state
# se répare en restaurant la version précédente.
terraform {
  backend "gcs" {
    bucket = "churn-predictor-tfstate"
    prefix = "cluster"
  }
}
