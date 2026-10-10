# GitHub Actions Workflow for switch-jobs-engine Deployment

This repository contains a GitHub Actions workflow that automates the deployment of the Switch Jobs Engine to Google Cloud Platform using Terraform.

## Workflow File
`.github/workflows/deploy-terraform-gcp.yml`

## Trigger Events
- Push to `main` branch
- Manual workflow dispatch (via GitHub UI or API)

## Required Secrets

To use this workflow, you need to configure the following secrets in your GitHub repository:

### Google Cloud Authentication (Workload Identity Federation)
- `GCP_WORKLOAD_IDENTITY_PROVIDER`: The workload identity provider resource name
- `GCP_SERVICE_ACCOUNT`: The service account email that has permissions to deploy resources
- `GCP_PROJECT_ID`: Your Google Cloud project ID

### Application Secrets
- `OPENROUTER_API_KEY`: OpenRouter API key for LLM access
- `LANGFUSE_PUBLIC_KEY`: (Optional) Langfuse public key for observability
- `LANGFUSE_SECRET_KEY`: (Optional) Langfuse secret key for authentication

## Input Parameters (for workflow_dispatch)
- `image_tag`: Container image tag (defaults to git SHA if not specified)
- `enable_worker_job`: Boolean to enable/disable background Cloud Run Job (default: false)
- `allow_unauthenticated`: Boolean to allow unauthenticated access to the service (default: false)

## Workflow Steps
1. **Build & Push Container Image**
   - Authenticates to Google Cloud using Workload Identity Federation
   - Builds the Docker image from the repository
   - Pushes the image to Artifact Registry

2. **Terraform Apply**
   - Authenticates to Google Cloud
   - Initializes Terraform with GCS backend
   - Validates the Terraform configuration
   - Plans the deployment
   - Applies the changes to deploy the infrastructure

## Terraform Variables
The workflow sets the following Terraform variables via environment variables:
- `TF_VAR_image`: The container image URI built in the previous step
- `TF_VAR_openrouter_api_key`: From the OPENROUTER_API_KEY secret
- `TF_VAR_langfuse_public_key`: From the LANGFUSE_PUBLIC_KEY secret
- `TF_VAR_langfuse_secret_key`: From the LANGFUSE_SECRET_KEY secret
- `TF_VAR_enable_worker_job`: From workflow input
- `TF_VAR_allow_unauthenticated`: From workflow input

## Prerequisites
1. Set up Workload Identity Federation between GitHub and Google Cloud
2. Create a Terraform state bucket (as described in `infra/terraform/README.md`)
3. Enable required Google Cloud APIs (Cloud Run, Artifact Registry, Secret Manager, etc.)
4. Configure the secrets listed above in your GitHub repository

## Local Testing
You can test the workflow locally using `act`:
```bash
act -j deploy -s GCP_WORKLOAD_IDENTITY_PROVIDER="..." -s GCP_SERVICE_ACCOUNT="..." -s GCP_PROJECT_ID="..." -s OPENROUTER_API_KEY="..." 
```