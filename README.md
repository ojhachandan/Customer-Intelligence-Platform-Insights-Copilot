# Customer Intelligence Platform + Insights Copilot

Runnable, API-first MVP for order ingestion, customer segmentation, hybrid recommendations, semantic customer discovery, and grounded analytics answers.

## Start locally

```sh
cp .env.example .env
docker compose up --build -d
docker compose exec api cip ingest data/orders.csv
docker compose exec api cip features
docker compose exec api cip train
docker compose exec api cip recommend
docker compose exec api cip embed
docker compose exec api cip reports reports
```

Pull the default local Copilot model once Ollama is healthy:

```sh
docker compose exec ollama ollama pull llama3.2:3b
```

Open `http://localhost:8000/docs` for the generated API documentation. The `scheduler` container runs the same jobs daily; set `CIP_SCHEDULE_SECONDS` for a shorter development cadence.

For a local Python environment instead of Docker, install `pip install -e '.[dev]'`, then run `cip init` followed by the pipeline commands below. Execute `pytest` to run the unit and integration-style service tests.

## API examples

```sh
curl http://localhost:8000/segment/c-001
curl http://localhost:8000/recommend/c-001
curl -X POST http://localhost:8000/copilot/ask -H 'content-type: application/json' \
  -d '{"question":"What is the 90 day revenue trend for segment 0?"}'
```

`/copilot/ask` returns structured citations alongside answer text. Numeric answers are generated only from a live tool call and are persisted with their input arguments in `copilot_audit_logs`.

## Pipeline commands

`cip init`, `cip ingest data/orders.csv`, `cip features`, `cip train`, `cip recommend`, `cip embed`, `cip reports reports`, and `cip drift` can be run independently. `train` records K-Means silhouette/elbow artifacts and its GMM baseline in the database and MLflow when `CIP_MLFLOW_TRACKING_URI` is configured.

Run `cip migrate` before a production deployment to apply the included Alembic schema migration. The API's `init` command is retained for frictionless local setup.

The recommendation engine uses implicit ALS and falls back to deterministic implicit-feedback co-occurrence if model fitting is unavailable. Customer profile vectors use a deterministic tabular hash embedding, making the local MVP self-contained while retaining Qdrant-compatible vector storage.

## Configuration and scope

All configuration uses the `CIP_` environment prefix; see `.env.example`. Endpoints are intentionally unauthenticated for local single-tenant use. Add API authentication through FastAPI dependencies before exposing the service outside a trusted environment.
