# Customer Intelligence Platform + Insights Copilot

The Customer Intelligence Platform is an end-to-end analytics system that turns raw e-commerce order data into customer segments, personalized recommendations, and a natural-language analytics assistant — built to demonstrate production engineering practices rather than a notebook exercise.

The pipeline ingests order-line data through an idempotent, schema-validated loader, computes versioned RFM and behavioral feature snapshots, and trains K-Means segmentation models (benchmarked against a Gaussian Mixture baseline) with full experiment tracking in MLflow. A hybrid recommendation engine blends implicit ALS collaborative filtering with content-based similarity, with cold-start fallbacks and Redis-backed caching for low-latency serving.

At the center of the system is the Insights Copilot — a LangGraph-orchestrated agent that answers natural-language business questions by calling live tools against the feature store, time-series warehouse data, and a Qdrant vector store of customer behavioral embeddings. Every numeric claim the Copilot makes is grounded and cited to its originating tool call or source report; when a question can't be answered from available data, it states that limitation explicitly rather than fabricating a number. Every request — prompt, tool arguments, sources, response, latency, and model metadata — is persisted to an audit log for full traceability.

The system runs entirely through Docker Compose (Postgres, Redis, Qdrant, MLflow, API, scheduler) and defaults to a local Ollama model, so it's fully reproducible with zero external API costs, while remaining provider-agnostic for hosted LLMs. Population stability index (PSI) drift reporting tracks segment stability across pipeline runs, and the API is fully documented via FastAPI's OpenAPI interface.

This project was deliberately engineered around the failure modes that matter in production ML systems: data validation at ingestion, model versioning and comparison, cache invalidation, grounded rather than hallucinated agent outputs, and full auditability of every AI-generated claim.
