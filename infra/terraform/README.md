# Terraform Deployment for switch-jobs-engine

This directory contains Terraform configuration to deploy the Switch Jobs Engine to Google Cloud Platform.

## Architecture

- **Cloud Run service** (`google_cloud_run_v2_service.service`): Runs the FastAPI app (`app/main.py`) from the Docker image.
- **GCS bucket** (`google_storage_bucket.gcs`): Persistent storage for the `GCSStorage` backend (JSON documents under collections/doc_id.json).
- **Artifact Registry** (`google_artifact_registry_repository.repo`): Stores container images.
- **Secret Manager** (`google_secret_manager_secret.*`): Stores the OpenRouter API key and optional Langfuse credentials.
- **Service Account** (`google_service_account.sje_runtime`): Least-privilege identity for the Cloud Run service.
- **Cloud Run Job** (`google_cloud_run_v2_job.worker`): Background worker for long-running ingestion (gated behind `var.enable_worker_job`).

## Prerequisites

1. Install the Google Cloud CLI (`gcloud`): https://cloud.google.com/sdk/docs/install
2. Authenticate: `gcloud auth login` and `gcloud auth application-default login`
3. Set your project: `gcloud config set project <PROJECT_ID>`
4. Enable billing on the project.
5. Install Terraform: https://developer.hashicorp.com/terraform/downloads

## Bootstrap

Create a state bucket manually (Terraform can't create its own backend in the same config):

```bash
gcloud storage buckets create gs://switch-jobs-engine-tfstate \
  --location=us-central1 \
  --uniform-bucket-level-access
```

Then initialize Terraform:

```bash
cd infra/terraform
terraform init
```

## Configuration

Copy the example variables file:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values. **Never commit `terraform.tfvars`** (see `.gitignore`).

Secrets are provided via environment variables or the `.tfvars` file. They are marked `sensitive` and never appear in Terraform state.

## Deployment

### 1. Build and push the container image

```bash
# Tag the image for Artifact Registry
docker tag switch-jobs-engine:latest \
  us-docker.pkg.dev/<PROJECT_ID>/switch-jobs-engine-repo/switch-jobs-engine:latest

# Push to Artifact Registry
docker push us-docker.pkg.dev/<PROJECT_ID>/switch-jobs-engine-repo/switch-jobs-engine:latest
```

Or use Cloud Build:

```bash
gcloud builds submit \
  --tag us-docker.pkg.dev/<PROJECT_ID>/switch-jobs-engine-repo/switch-jobs-engine:latest
```

### 2. Plan and apply

```bash
cd infra/terraform
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars -auto-approve
```

### 3. Verify

```bash
terraform output service_url
curl $(terraform output service_url)/health
```

## Destroy

```bash
terraform destroy -var-file=terraform.tfvars -auto-approve
```

## Notes

- The Cloud Run service uses `STORAGE_BACKEND=gcs` and reads `GCS_BUCKET`/`GCS_PREFIX` from environment variables.
- The `app.worker` module is not yet implemented (see `AGENTS.md` Known Gaps). The Cloud Run Job is gated behind `var.enable_worker_job` (default: `false`).
- For production, set `allow_unauthenticated = false` and use `gcloud run services add-iam-policy-binding` to restrict access.
- The default `log_level = "INFO"` can be overridden via `terraform.tfvars`.
- OpenTelemetry is disabled by default (`otel_enabled = false`). Enable it only if you have an OTLP collector available.