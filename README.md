# The Qasar — Customer Intelligence Platform + Insights Copilot

An enterprise-grade, dataset-aware, API-first Customer Intelligence Platform and AI Insights Copilot powered by the official real-world **UCI Online Retail II** dataset.

Provides end-to-end streaming data ingestion, strict dataset isolation, audited financial reconciliation, leakage-safe RFM feature engineering, K-Means & Gaussian Mixture Model segmentation, hybrid ALS collaborative filtering recommendations, 32-dimensional normalized behavioral similarity search (Qdrant), PSI drift monitoring, and a grounded LangGraph AI Insights Copilot.

---

## 1. Primary Dataset: UCI Online Retail II

- **Repository**: [UCI Machine Learning Repository — Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii)
- **Dataset ID**: `502`
- **DOI**: `10.24432/C5CG6D`
- **Creator**: Dr. Daqing Chen, London South Bank University
- **License**: Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Historical Coverage**: 01 December 2009 to 09 December 2011 (24 months)
- **Source Currency**: British Pound Sterling (GBP / £)
- **Total Source Records**: **1,067,371** exact rows across two worksheets:
  - `Year 2009-2010`: 525,461 rows
  - `Year 2010-2011`: 541,910 rows
- **Raw File Verification**: `data/raw/online_retail_II.xlsx` (45,622,278 bytes, SHA-256: `bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980`).

---

## 2. Dataset Architecture & Strict Isolation

The platform enforces strict context separation between datasets via the `DatasetRegistry` table:

| Dataset Identifier | Nature | Coverage | Records | Primary Currency |
|---|---|---|---|---|
| `seed_demo` | Synthetic baseline fixture | Unit test fixture | 10 order lines | USD / converted INR |
| `uci_online_retail_ii_v1` | Official UCI Online Retail II | 2009-12-01 to 2011-12-09 | 1,067,371 rows | GBP (£) |

Datasets are isolated at the database, feature store, clustering, recommendation, embedding, and Copilot levels. Composite primary/unique keys prevent ID collisions across datasets.

---

## 3. Audited Financial Reconciliation Ledger (GBP)

The warehouse implements a double-entry financial reconciliation ledger computed from the underlying 1,067,371 transaction rows:

| Financial Metric | Verified Value | Definition / Calculation |
|---|---|---|
| **Gross Merchandise Sales** | **£20,108,883.20** | Sum of eligible positive merchandise sales on normal sales invoices |
| **Cancellations** | **-£1,526,667.86** | Signed adjustments across 8,292 cancellation credit invoices (`InvoiceNo` starting with `C`) |
| **Other Non-Product Charges** | **£705,035.23** | Adjustments for postage (`POST`), bank charges, and manual fees |
| **Net Merchandise Revenue** | **£18,582,215.34** | Gross Sales + Cancellations + Returns (audited net ledger) |
| **Eligible Sales Invoices** | **39,516** | Distinct completed purchase invoices |
| **Active Purchasing Customers** | **5,852** | Distinct identified customers with at least one completed purchase |
| **Repeat Customers** | **4,234** | Customers with ≥ 2 purchase invoices (**72.35% repeat rate**) |
| **Gross Average Order Value (AOV)** | **£508.88** | Gross Merchandise Sales / 39,516 sales invoices |
| **Net Average Order Value (AOV)** | **£470.25** | Net Merchandise Revenue / 39,516 sales invoices |

---

## 4. Machine Learning & Analytics Architecture

1. **Customer Feature Store (`FeatureSnapshot`)**:
   - Leakage-safe snapshot computation (`ordered_at <= as_of_timestamp`).
   - RFM metrics: Recency (days), Frequency (invoices), Monetary (net spend in GBP).
   - Behavioral signals: Gross spend, returns/cancellations, purchase tenure, average purchase interval, unique products, total quantity, and category affinity vectors.
   - Distinct separation of purchase timestamps from cancellation/refund activities.
2. **Customer Segmentation (`KMeans` & `GaussianMixture`)**:
   - Feature normalization with `StandardScaler`.
   - Candidate evaluation across $k \in [2, 6]$ using elbow inertia and silhouette scores.
   - Selected model: $k=3$ with silhouette score **0.8303** (vs. GMM baseline of **0.4161**) across all 5,942 customers.
   - Grounded cluster descriptions generated dynamically from cluster centroids.
   - MLflow experiment and artifact tracking.
3. **Hybrid Recommender Engine (`Recommendation`)**:
   - Implicit Alternating Least Squares (ALS) matrix factorization blended with category-content affinity ($0.7 \times \text{ALS} + 0.3 \times \text{Content}$).
   - Fast SQL-aggregated cold-start popularity fallback.
   - Precomputed recommendations for all 5,852 purchasing customers.
   - Chronological offline evaluation: Precision@10, Recall@10, NDCG@10, catalog coverage, and user coverage.
4. **Normalized Behavioral Similarity Search (Qdrant)**:
   - 32-dimensional deterministic normalized behavioral numerical embedding:
     - Dimensions 0–7: Log1p-scaled RFM, AOV, tenure, interval, quantity, and product diversity.
     - Dimensions 8–31: Deterministically projected category affinity tokens.
   - L2 normalized for cosine distance similarity in dataset-isolated collections (`customer_profiles_{dataset_id}`).

---

## 5. LangGraph AI Insights Copilot

The Copilot routes natural-language business queries to 14 predefined, typed analytical tools:

1. `get_business_overview`: High-level revenue, orders, customers, and AOV.
2. `get_revenue_trend`: Time-series revenue trend over time.
3. `get_revenue_reconciliation`: Audited gross merchandise sales, cancellations, and net revenue.
4. `get_customer_profile`: Comprehensive customer profile, RFM, and purchase tenure.
5. `get_customer_rfm`: Targeted RFM metrics.
6. `get_segment_performance`: Revenue, customer count, and contribution per segment.
7. `get_product_performance`: Top-selling products by quantity and revenue.
8. `get_customer_recommendations`: Personalized hybrid recommendations for a customer.
9. `search_similar_customers`: Qdrant behavioral similarity search.
10. `get_geographic_analytics`: Revenue and customer breakdown across countries.
11. `get_return_analytics`: Cancellation and return rates and credit note totals.
12. `search_business_reports`: Semantic discovery over narrative reports.
13. `get_model_information`: Active model version, algorithm, $k$, and silhouette metrics.
14. `get_drift_information`: Feature-level Population Stability Index (PSI).

All numeric statements cite empirical tool evidence and are audited to `copilot_audit_logs`. Responses explicitly identify the dataset context (UCI Online Retail II, 2009–2011) and format values in GBP (£).

---

## 6. CLI Management Commands

The `cip` CLI manages the complete data and intelligence lifecycle:

```sh
# Dataset acquisition and inspection
cip dataset download               # Download official UCI workbook (45.6 MB)
cip dataset inspect                # Inspect sheets and verify 1,067,371 rows
cip dataset manifest               # Generate machine-readable JSON manifest
cip dataset validate --sample 5000 # Run dry-run data quality validation

# Ingestion and activation
cip dataset import --batch-size 15000  # Streaming idempotent ingestion into DB
cip dataset report                     # View persisted data quality JSON report
cip dataset activate uci_online_retail_ii_v1 # Atomically activate dataset context
cip dataset status                     # Inspect active dataset metadata
cip dataset rollback                   # Revert active context to seed_demo

# Analytical and ML pipelines (dataset-scoped via --dataset flag)
cip features --dataset uci_online_retail_ii_v1     # Generate RFM feature snapshots
cip train --dataset uci_online_retail_ii_v1        # Train KMeans & GMM models
cip recommend --dataset uci_online_retail_ii_v1    # Compute hybrid recommendations
cip evaluate-recommendations                       # Run chronological offline evaluation
cip embed --dataset uci_online_retail_ii_v1        # Sync 32-dim behavioral vectors
cip drift --dataset uci_online_retail_ii_v1        # Calculate feature-level PSI drift
```

---

## 7. REST API Endpoints

FastAPI exposes dataset-aware endpoints on port 8000:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health, active dataset, and feature version |
| `GET` | `/ready` | Database connection and dataset readiness probe |
| `GET` | `/datasets` | List all registered datasets in registry |
| `GET` | `/datasets/active` | Active dataset metadata, row counts, and date range |
| `GET` | `/analytics/overview` | High-level gross/net revenue, orders, AOV, and customers |
| `GET` | `/analytics/reconciliation` | Audited financial ledger (sales, returns, cancellations) |
| `GET` | `/analytics/returns` | Cancellation rate and credit note totals |
| `GET` | `/analytics/geographic` | Revenue and order distribution by country |
| `GET` | `/analytics/segments` | Segment revenue contributions and customer counts |
| `GET` | `/analytics/products` | Best-selling product rankings |
| `GET` | `/analytics/revenue-trend` | Time-series revenue trend |
| `GET` | `/customer/{id}` | Customer profile, RFM, and tenure |
| `GET` | `/segment/{id}` | Customer segment assignment and model version |
| `GET` | `/recommend/{id}` | Personalized hybrid product recommendations |
| `GET` | `/recommendations/evaluation` | Offline Precision@K, Recall@K, and NDCG@K metrics |
| `GET` | `/datasets/quality-report` | Persisted data quality profiling report |
| `POST` | `/copilot/ask` | LangGraph Copilot query with evidence citations |
| `GET` | `/copilot/audit/{id}` | Retrieve persisted Copilot audit execution log |

---

## 8. Verification & Quality Gates

Run the test suite and static checks locally:

```sh
# Execute full backend test suite (31 tests)
pytest tests/

# Execute Ruff linter
ruff check .

# Execute database migrations
alembic upgrade head
```

### Frontend Notice
The `frontend/` directory is strictly preserved. All 73 frontend files match baseline SHA-256 hashes byte-for-byte.
