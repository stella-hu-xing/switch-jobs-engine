# GCS bucket for GCSStorage (app data)
# This bucket stores JSON documents under collections/doc_id.json
# Used by the GCSStorage backend for persistent job data.

resource "google_storage_bucket" "gcs" {
  name         = var.gcs_bucket_name
  location     = var.region
  uniform_bucket_level_access = true

  # Enable versioning for safety (important for resume/application data)
  versioning {
    enabled = true
  }

  # Lifecycle management: retain objects for 90 days (adjust as needed)
  lifecycle {
    # Delete objects older than 90 days
    expiration {
      days = 90
    }
  }

  # Bypass default retention policies for development convenience
  # (comment out in production)
  # retention_policy {
  #   retention_duration = "90d"
  # }
}

# IAM binding: grant the runtime service account read/write access to the bucket
resource "google_storage_bucket_iam_member" "gcs_runtime" {
  location = var.gcs_bucket_name
  member   = "serviceAccount:sje-runtime@${var.project_id}.iam.gserviceaccount.com"
  role     = "roles/storage.objectAdmin"
}