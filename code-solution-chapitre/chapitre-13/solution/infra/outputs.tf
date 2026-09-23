output "cluster_endpoint" {
  value       = google_container_cluster.churn_cluster.endpoint
  description = "Adresse de l'API server, consommée par `gcloud container clusters get-credentials`."
  sensitive   = true
}

output "cluster_name" {
  value       = google_container_cluster.churn_cluster.name
  description = "Nom du cluster, à passer à kubectl et Helm."
}
