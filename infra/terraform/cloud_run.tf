# Cloud Run service for the Switch Jobs Engine
# Deploys the FastAPI application (app/main.py) as a container.
# Uses the GCS bucket for persistent storage (GCSStorage backend).

resource "google_cloud_run_v2_service" "service" {
  name          = var.service_name
  location      = var.region
  template      = {
    spec = {
      containers = [{
        image = var.image
        ports = [{
          container_port = 8080
        }]
      }]
    }
  }
  traffic = {
    percent = 100
  }

  # Use the dedicated runtime service account
  service_account = "sje-runtime@${var.project_id}.iam.gserviceaccount.com"

  # For single-user personal tool: do NOT expose publicly without explicit auth
  # ingress is omitted here, keeping it private (caller must use identity token)
  ingress = "ALLOW_ALL"  # only if allow_unauthenticated is true in variables
}