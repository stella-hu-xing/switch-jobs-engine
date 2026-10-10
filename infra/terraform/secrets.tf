# Secret Manager secrets for the Switch Jobs Engine
# Values are injected via TF_VAR_* (never committed to version control).
# In production, populate these via a .tfvars file or CI/CD pipeline.

# OpenRouter API key (stored in Secret Manager)
resource "google_secret_manager_secret" "openrouter_api_key" {
  name        = "openrouter-api-key"
  description = "OpenRouter API key for LLM calls"
  labels = {
    owner = "switch-jobs-engine"
  }
}

# Langfuse public key (optional, for language fuzzing)
resource "google_secret_manager_secret" "langfuse_public_key" {
  name        = "langfuse-public-key"
  description = "Langfuse public key for language similarity analysis"
  labels = {
    owner = "switch-jobs-engine"
  }
}

# Langfuse secret key (optional, for authentication)
resource "google_secret_manager_secret" "langfuse_secret_key" {
  name        = "langfuse-secret-key"
  description = "Langfuse secret key for authentication"
  labels = {
    owner = "switch-jobs-engine"
  }
}

# Note: Secrets are referenced by name in other resources (e.g., cloud_run_v2_service).
# They are NOT included in the Terraform state because their values are sensitive.
