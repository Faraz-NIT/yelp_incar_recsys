# Common workflow shortcuts. `make help` lists them.
.PHONY: help setup sample-data pipeline app docker-build docker-run docker-up docker-down lint format test clean

PY ?= python

help:  ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[1;36m%-18s\033[0m %s\n", $$1, $$2}'

setup:  ## Create the conda env from environment.yml.
	conda env create -f environment.yml

sample-data:  ## Generate synthetic Yelp-format data into data/raw/.
	$(PY) scripts/make_sample_data.py --n-users 600 --n-businesses 300

pipeline:  ## Run preprocess + sentiment + train + evaluate end-to-end.
	$(PY) scripts/run_pipeline.py

app:  ## Launch the Streamlit app locally.
	streamlit run app/app.py

docker-build:  ## Build the Docker image.
	docker build -t yelp-incar-recsys:latest .

docker-run: docker-build  ## Build then run the container with mounted data/models.
	docker run --rm -p 8501:8501 \
		-v $$(pwd)/data:/app/data \
		-v $$(pwd)/models:/app/models \
		-e GROQ_API_KEY=$${GROQ_API_KEY:-} \
		yelp-incar-recsys:latest

docker-up:  ## docker-compose up (detached).
	docker compose up -d

docker-down:  ## docker-compose down.
	docker compose down

lint:  ## Run pycodestyle.
	pycodestyle src app scripts --max-line-length 100 --ignore=E203,E501,W503

format:  ## Apply black + isort.
	isort src app scripts tests
	black src app scripts tests

test:  ## Run unit tests.
	pytest tests -v

clean:  ## Remove caches & build artefacts (keeps data/models on disk).
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ipynb_checkpoints -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
