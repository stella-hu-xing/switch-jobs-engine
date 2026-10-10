# Dedicated runtime service account for Cloud Run
# Uses least-privilege principle: only the permissions needed for the service.

resource "google_service_account" "sje_runtime" {
  name        = "sje-runtime"
  display_name = "Switch Jobs Engine Cloud Run Runtime"
}

# Grant the service account read/write access to the GCS bucket
resource "google_storage_bucket_iam_member" "gcs_runtime" {
  location = var.gcs_bucket_name
  member   = "serviceAccount:sje-runtime@${var.project_id}.iam.gserviceaccount.com"
  role     = "roles/storage.objectAdmin"
}

# Grant the service account the ability to access secrets in Secret Manager
resource "google_secret_manager_secret_iam_member" "gcs_runtime" {
  for_each = toset(["openrouter-api-key", "langfuse-public-key", "langfuse-secret-key"])
  location = each.value
  member   = "serviceAccount:sje-runtime@${var.project_id}.iam.gserviceaccount.com"
  role     = "roles/secretmanager.secretAccessor"
}

# Grant the service account the ability to manage Cloud Run resources
resource "google_project_iam_member" "sje_runtime_cr_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:sje-runtime@${var.project_id}.iam.gserviceaccount.com"
}

# Grant the service account the ability to manage Cloud Build resources (needed for --source deploys)
resource "google_project_iam_member" "sje_runtime_cloudbuild" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.editor"
  member  = "serviceAccount:sje-runtime@${var.project_id}.iam.gserviceaccount.com"
}
