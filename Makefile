PY ?= .venv/bin/python
PIP ?= .venv/bin/pip
SERVICE ?= switch-jobs-engine
REGION ?= europe-west1

.PHONY: venv install dev run test fmt docker-build docker-run deploy clean

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

deploy:
	gcloud run deploy $(SERVICE) \
		--source . \
		--region $(REGION) \
		--platform managed \
		--set-env-vars STORAGE_BACKEND=gcs

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache
