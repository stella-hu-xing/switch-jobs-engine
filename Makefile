PY ?= .venv/bin/python
PIP ?= .venv/bin/pip
SERVICE ?= switch-jobs-engine
REGION ?= europe-west1
AR_IMAGE ?= us-docker.pkg.dev/$(PROJECT_ID)/$(SERVICE)-repo/$(SERVICE):$(TAG)

.PHONY: venv install dev run test fmt docker-build docker-run deploy deploy-quick clean
.PHONY: tf-init tf-plan tf-apply tf-destroy tf-bootstrap

venv:
	python3 -m venv .venv
	$(PIP) install --upgrade pip

install: venv
	$(PIP) install -r requirements.txt

dev run:
	$(PY) -m uvicorn app.main:app --reload --port 8000

test:
	$(PY) -m pytest -q

docker-build:
	docker build -t $(SERVICE):local .

docker-run:
	docker run --rm -p 8000:8080 --env-file .env $(SERVICE):local

# Build and push the container image to Artifact Registry
docker-push:
	gcloud builds submit --tag $(AR_IMAGE) --quiet

# Terraform: bootstrap (initialize state backend, set up workspace state)
tf-bootstrap:
	cd infra/terraform && \
	tf switch new production && \
	tf init

# Terraform: init (backend, providers)
tf-init:
	cd infra/terraform && terraform init

# Terraform: plan
tf-plan:
	cd infra/terraform && terraform plan -var-file=terraform.tfvars

# Terraform: apply
tf-apply:
	cd infra/terraform && terraform apply -var-file=terraform.tfvars -auto-approve

# Terraform: destroy
tf-destroy:
	cd infra/terraform && terraform destroy -var-file=terraform.tfvars -auto-approve

# Deploy via Terraform (build image, then apply infra)
deploy: docker-push tf-apply

# Legacy: direct Cloud Run deploy (bypasses Terraform; use for quick local iteration only)
deploy-quick:
	gcloud run deploy $(SERVICE) \
		--source . \
		--region $(REGION) \
		--platform managed \
		--set-env-vars STORAGE_BACKEND=gcs

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache
