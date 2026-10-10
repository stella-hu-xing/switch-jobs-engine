terraform {
  required_version = ">= 1.6.0"

  backend "gcs" {
    bucket         = "switch-jobs-engine-tfstate"
    prefix         = "terraform/state"
    project        = var.project_id
    region         = var.region
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "run" {
  project = var.project_id
  service = "run.googleapis.com"
  depends_on = [
    google_project_service.artifact_registry,
    google_project_service.storage,
    google_project_service.secret_manager,
    google_project_service.iam,
    google_project_service.cloudbuild,
  ]
}

resource "google_project_service" "artifact_registry" {
  project = var.project_id
  service = "artifactregistry.googleapis.com"
}

resource "google_project_service" "storage" {
  project = var.project_id
  service = "storage.googleapis.com"
}

resource "google_project_service" "secret_manager" {
  project = var.project_id
  service = "secretmanager.googleapis.com"
}

resource "google_project_service" "iam" {
  project = var.project_id
  service = "iam.googleapis.com"
}

resource "google_project_service" "cloudbuild" {
  project = var.project_id
  service = "cloudbuild.googleapis.com"
}