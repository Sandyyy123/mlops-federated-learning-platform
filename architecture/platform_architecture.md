# Werkstatt AI Platform Architecture

## 1. Goals

- Productionise three pre-trained ML modules behind one customer-facing platform.
- Stay below EUR 200 per month total infrastructure cost.
- Run on one workstation-class GPU box with a clean upgrade path to a multi-node Kubernetes cluster.
- Keep tenant data isolated; prevent any cross-tenant feature, prediction, or log leakage.

## 2. High-level topology

```
+---------------------- Werkstatt AI Control Plane --------------------+
|  Auth (Keycloak)   Model Registry (MLflow)   Feature Store (PG)     |
|  Orchestrator (Airflow)   Logging (Loki)   Metrics (Prometheus)     |
+----------------------------------------------------------------------+
                                |
                                v
+------------- Module A ---------+ +-------- Module B ----------+ +----- Module C ------+
|  Olist Customer Satisfaction   | |  Rakuten Multimodal        | |  MVTec-style        |
|  (binary classification)       | |  Product Classifier        | |  Anomaly Detector   |
|  source: 02_supply_chain_csat  | |  source: 06_rakuten_multi. | |  source: 07_indust. |
|  inference: FastAPI (CPU)      | |  inference: FastAPI (GPU)  | |  inference: FastAPI |
|  feature store: Postgres view  | |  feature store: image refs | |  (GPU)              |
+--------------------------------+ +----------------------------+ +---------------------+
                                |
                                v
                       +----------------+
                       |  API Gateway   |  -- Traefik with per-tenant TLS
                       |  (Traefik)     |
                       +----------------+
                                |
                       Tenant 1 ... Tenant N (workshops)
```

## 3. Shared services

### 3.1 Authentication
Keycloak issues OIDC tokens. Each tenant maps to a Keycloak realm. The API gateway validates tokens and injects a tenant header that downstream modules read. Module code never trusts a tenant claim it has not verified at the gateway.

### 3.2 Model registry
MLflow Tracking Server stores experiments and registered models. Each federated module registers its production model under a namespaced name: `werkstatt.csat.olist`, `werkstatt.catalog.rakuten`, `werkstatt.qc.anomaly`. Promotion stages are `Staging` and `Production`. The inference services pull the model URI by stage at startup; they do not hard-code paths.

### 3.3 Feature store
A thin Postgres-backed feature store with two schemas:
- `online`: low-latency rows, served via SQL views, refreshed by streaming jobs.
- `offline`: batch tables for training, identical schema as online, refreshed nightly by Airflow.
The same SQL view definition is used at training and serving time to prevent training-serving skew (a known source of silent failures, see Sambasivan 2021 on data cascades).

### 3.4 Orchestrator
Airflow 2.x runs in `LocalExecutor` mode. Three DAGs:
- `csat_retrain_weekly`
- `catalog_retrain_monthly`
- `anomaly_retrain_monthly`
Each DAG: extract -> validate (TFDV) -> train -> evaluate -> register -> notify. Failure on any step blocks promotion to Production.

### 3.5 Monitoring
Prometheus scrapes module endpoints on `/metrics`. Grafana dashboards per module:
- request rate, p50 and p95 latency, error rate
- prediction distribution (rolling 24 h)
- input feature distribution drift (PSI per feature)
Alertmanager pages on: error rate above 1 percent for 5 minutes, p95 latency above SLO, drift above PSI 0.25.

## 4. Per-module deployment

Each module is one Docker image. The image entrypoint is `uvicorn app:api`. A standard `Dockerfile` template lives at `infrastructure/Dockerfile` (referenced, not generated here). All three images expose the same five endpoints:

```
GET  /healthz            liveness
GET  /readyz             readiness, includes model load check
GET  /metrics            Prometheus exposition
POST /predict            inference, takes tenant_id from JWT
GET  /model/info         current model URI and stage
```

## 5. Cost ceiling

Hard target EUR 200 per month total. Allocation:
- workstation electricity: about EUR 60 to 80 per month assuming 12 h on
- object storage for artefacts (S3-compatible, MinIO self-hosted): EUR 0
- Postgres, Redis, Prometheus, Grafana, MLflow, Airflow: all self-hosted, EUR 0
- domain plus TLS plus monitoring uptime checks: about EUR 10 per month
- backup S3 (off-site): about EUR 10 per month
- buffer for paid managed services if a customer demands it: EUR 100 per month

If any tenant requires GPU autoscaling beyond the workstation, the architecture allows a clean lift-and-shift to a single-node K3s plus GPU cloud burst, but that is a v1.0 decision, not v1.0.

## 6. GPU-tier cascade

Inference uses a three-tier cascade to keep GPU usage minimal:
1. Tier 1 (CPU): cached predictions, simple sklearn models (Module A baseline). Free.
2. Tier 2 (small GPU): quantised CNN, small batch (Module B). Used for catalogue identification when Tier 1 confidence is low.
3. Tier 3 (full GPU): full-precision model (Module C anomaly detector). Used only when Tier 2 cannot decide.

The router decides escalation by confidence threshold. Tier 3 calls are logged with reason so the cost monitor can alert if the cascade is misconfigured.

## 7. Security boundaries

- All inter-service traffic goes through Traefik. No service is exposed publicly except the gateway.
- Per-tenant database schemas. Postgres role-based access enforces the boundary.
- Secrets in HashiCorp Vault dev mode (v1.0) or AWS Secrets Manager (v1.0). Never in the image.
- Image scanning in CI (Trivy). Builds fail on critical CVEs.

## 8. Reliability targets (SLO draft for v1.0)

| Module | Availability | p95 latency | Error rate |
|--------|--------------|-------------|------------|
| A CSAT | 99.5 percent | 200 ms      | below 0.5 percent |
| B Catalogue | 99.0 percent | 800 ms | below 1 percent |
| C Anomaly | 99.0 percent | 1.5 s    | below 1 percent |

These are draft targets to be ratified after the first month of Production traffic.
