# Werkstatt AI Capstone (Modul 2 MLOps Umbrella)

**Project number:** 22
**Liora module:** Modul 2 (MLOps), 266 UE, deadline 26 October 2026, cohort 6974
**Methodology:** MLOps platform / federated module orchestration. **No standalone ML model.** This is an umbrella that productionises three completed Liora projects.
**Output folder:** `/root/AI/liora_projects/22_werkstatt/`

## Federated modules

| Slot | Source project | Task type | Role on the platform |
|------|----------------|-----------|----------------------|
| A    | #2 Olist Customer Satisfaction (`02_supply_chain_csat`) | Binary classification on tabular review data | "Customer-pulse" microservice for after-sales review scoring |
| B    | #6 Rakuten Multimodal Product Classification (`06_rakuten_multimodal`) | Computer vision plus NLP, multi-class | Catalogue and parts identification microservice |
| C    | #7 Industrial Anomaly Detection (`07_industrial_anomaly`) | Image-based anomaly detection | Quality control microservice on the workshop floor |

The capstone is branded "Werkstatt AI" because the target buyer is the DACH industrial Mittelstand (workshops, parts suppliers, after-sales and service operations). All three federated modules answer questions a workshop owner already asks: are my customers happy, is this part what we say it is, is this casting defective.

## Why an umbrella project, not a fourth model

Liora Modul 2 is graded on MLOps competency, not on a fourth ML algorithm. Building one more model adds no new evidence of MLOps skill. A platform that productionises three already-trained models exercises every Modul 2 learning objective in one deliverable:

- containerisation (Docker)
- pipeline orchestration (Airflow)
- model registry and feature store (MLflow plus a thin Postgres-backed feature store)
- model serving (FastAPI plus an inference router)
- monitoring (Prometheus plus Grafana plus drift detection)
- CI/CD (GitHub Actions skeleton)
- multi-tenant isolation (per-customer namespaces and per-module auth)
- cost control (GPU-tier cascade, hard EUR 200 per month ceiling)

## Modul 2 mapping

| Modul 2 learning objective | Werkstatt AI artefact |
|----------------------------|------------------------|
| Reproducible training pipelines | `infrastructure/airflow_dag_skeleton.py` |
| Containerised inference services | `infrastructure/fastapi_skeleton.py`, `infrastructure/docker-compose.yml` |
| Centralised model registry | MLflow service in `docker-compose.yml` |
| Monitoring and observability | `infrastructure/prometheus_grafana_notes.md` |
| Multi-tenant deployment topology | `architecture/platform_architecture.md`, `architecture/module_integration.md` |
| Drift detection and retraining triggers | Drift section in `manuscripts/manuscript.md`, references 9 to 12 |
| Cost-aware engineering on a single GPU box | Cost section in manuscript, GPU cascade in architecture |

## Phase 1 deliverables (this scaffold)

- `brief.md` (this file)
- `architecture/platform_architecture.md` - federated layout, shared services
- `architecture/module_integration.md` - how the three modules plug in
- `architecture/data_flow_diagram.md` - Mermaid plus ASCII
- `infrastructure/docker-compose.yml` - sample multi-service compose
- `infrastructure/airflow_dag_skeleton.py` - DAG outline for one pipeline
- `infrastructure/fastapi_skeleton.py` - inference API outline
- `infrastructure/prometheus_grafana_notes.md`
- `reports/references.md` - 27 verified MLOps references
- `manuscripts/manuscript.md` - 4000 to 5000 word IMRaD adaptation
- `deliverables/presentation.html` - federated platform diagram with per-module integration view
- `checkpoint.json` - phase 1 status

## Out of scope for Phase 1

- No model training scripts (the three federated models live in projects #2, #6, #7 and remain untouched, per agent rules 7 and 8).
- No actual deployment. Skeletons only. Main session executes after all 14 agents finish.
- No GitHub push (handled by main session).

## Author

Sandeep Grover, Liora MLE Programme, Cohort 6974, Modul 2 MLOps capstone.
