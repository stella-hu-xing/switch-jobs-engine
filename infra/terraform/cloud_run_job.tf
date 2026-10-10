# Cloud Run Job for background ingestion/enrichment (not yet implemented)
# This resource is gated behind `var.enable_worker_job` (defaults to false)
# because the `app/worker.py` module does not exist yet.

resource "google_cloud_run_v2_job" "worker" {
  name      = "sje-worker"
  location  = var.region
  template  = {
    spec = {
      containers = [{
        image = var.image
        command = ["python", "-m", "app.worker"]
      }]
    }
  }
  # No trigger specified - intended to be invoked manually or via Cloud Scheduler
  # when the worker module is implemented.
  # For now, this job exists but won't run on a schedule.
}