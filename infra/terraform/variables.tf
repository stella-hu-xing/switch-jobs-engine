variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "europe-west1"
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "switch-jobs-engine"
}

variable "gcs_bucket_name" {
  description = "Name of the GCS bucket used for GCSStorage (app data)"
  type        = string
  default     = "switch-jobs-engine-data"
}

variable "gcs_prefix" {
  description = "Prefix within the GCS bucket for app documents"
  type        = string
  default     = "switch-jobs-engine"
}

variable "image" {
  description = "Full Artifact Registry image reference for the Cloud Run container (e.g. us-docker.pkg.dev/project/repo/svc:v1). If empty, --source build is used via gcloud and this service is created afterward."
  type        = string
}

variable "openrouter_api_key" {
  description = "OpenRouter API key (stored in Secret Manager, not committed)"
  type        = string
  sensitive   = true
}

variable "langfuse_public_key" {
  description = "Langfuse public key (optional, omit if not using Langfuse)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "langfuse_secret_key" {
  description = "Langfuse secret key (optional, omit if not using Langfuse)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "allow_unauthenticated" {
  description = "Whether to allow unauthenticated invocations (single-user tool: keep false for production; caller provides identity token)"
  type        = bool
  default     = false
}

variable "enable_worker_job" {
  description = "Whether to deploy the background Cloud Run Job (app/worker.py) - not yet implemented, defaults to false"
  type        = bool
  default     = false
}

variable "otel_enabled" {
  description = "Enable OpenTelemetry exports (requires a reachable OTLP collector)"
  type        = bool
  default     = false
}

variable "otel_exporter_otlp_endpoint" {
  description = "OTLP endpoint for telemetry export"
  type        = string
  default     = "http://localhost:4318"
}

variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"
}