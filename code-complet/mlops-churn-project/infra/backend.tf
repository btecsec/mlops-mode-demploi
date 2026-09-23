terraform {
  backend "gcs" {
    bucket = "churn-predictor-tfstate"
    prefix = "cluster"
  }
}
