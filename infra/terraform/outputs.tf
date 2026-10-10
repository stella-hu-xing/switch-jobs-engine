# Outputs for the Terraform deployment

output "service_url" {
  description = "HTTP URL of the deployed Cloud Run service"
  value       = "https://${google_cloud_run_v2_service.service.status[0].url}"
}

output "gcs_bucket_name" {
  description = "Name of the GCS bucket used for app data"
  value       = var.gcs_bucket_name
}

output "service_name" {
  description = "Name of the Cloud Run service"
  value       = var.service_name
}

output "runtime_service_account" {
  description = "Service account email for the Cloud Run service"
  value       = "sje-runtime@${var.project_id}.iam.gserviceaccount.com"
}

output "image_tag" {
  description = "Image tag used for the Cloud Run service"
  value       = var.image
}
