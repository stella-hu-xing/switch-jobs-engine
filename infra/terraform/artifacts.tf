# Artifact Registry repository for storing container images
# This allows the Cloud Run service to pull images from a managed registry.

resource "google_artifact_registry_repository" "repo" {
  name        = "switch-jobs-engine-repo"
  format      = "DOCKER"
}
