> **Proprietary - All Rights Reserved.** Copyright (c) 2026 Sandeep Grover. This repository is licensed to Sandeep Grover and may not be used, run, copied, modified, distributed, or used to train models without prior written permission. Public visibility does not grant a license. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

---

# Werkstatt AI: A Federated MLOps Platform

A design-stage MLOps capstone for productionising three heterogeneous, already-trained ML modules (customer-satisfaction classifier, multimodal product classifier, anomaly detector) behind one shared control plane.

---

## Overview

Most small industrial workshops in the DACH region do not run production machine learning. The blocker is rarely the model; it is the operational layer that registers, serves, monitors, retrains, and isolates models across tenants.

This repository is the capstone deliverable for that operational layer. "Federated" here means a *federation of three independent modules* sharing one control plane (authentication, model registry, feature store, orchestrator, monitoring), not federated learning with on-device aggregation. The three modules are deliberately heterogeneous:

- Module A: Olist customer-satisfaction classifier (tabular, CPU, low latency)
- Module B: Rakuten-style multimodal product classifier (image plus text, GPU)
- Module C: MVTec-style industrial anomaly detector (image, full GPU)

Each module exposes the same five HTTP endpoints, emits the same metrics schema, and is governed by the same drift, retrain, and promotion rules, so one runbook and one dashboard template cover all three.

**Scope and status.** This repo contains the platform *architecture, serving contract, orchestration skeleton, reference infrastructure, and the written capstone* (manuscript plus verified references). It is a design and scaffold deliverable, not a fully implemented, runnable training-and-serving system. The Python files are intentionally skeletons: the FastAPI app factory and the Airflow DAG structure are concrete, while the module-specific bodies (model loading, prediction, feature extraction) are marked as later-stage work. See the flag at the end of this README.

---

## What is inside

- **Platform architecture** (`architecture/`): topology, per-module integration contract, and data-flow diagram.
- **Serving contract** (`infrastructure/fastapi_skeleton.py`): a reusable FastAPI app factory built around a `ModuleAdapter` protocol, with Prometheus metrics (request count, latency histogram, confidence histogram) and the five shared endpoints (`/healthz`, `/readyz`, `/metrics`, `/predict`, `/model/info`).
- **Orchestration skeleton** (`infrastructure/airflow_dag_skeleton.py`): a weekly retrain DAG (extract, validate, train, evaluate, register and promote, smoke test) with a metric-based promotion gate. Task bodies raise `NotImplementedError` by design at this stage.
- **Reference deployment** (`infrastructure/docker-compose.yml`): a multi-service stack (Traefik, Keycloak, Postgres, MinIO, MLflow, Airflow, Prometheus, Grafana, Loki, and the three module images). Provided as a reference configuration to adapt, not a one-command bring-up.
- **Monitoring notes** (`infrastructure/prometheus_grafana_notes.md`).
- **Capstone manuscript** (`manuscripts/manuscript.md`): IMRaD write-up of the federation design, cost envelope, and deployment plan.
- **References** (`reports/references.md`): citations verified against the CrossRef API.
- **Presentation and landing page** (`deliverables/presentation.html`, `index.html`).

---

## Tech stack

Observed from `requirements.txt`, the actual imports, and `docker-compose.yml`:

- **Language:** Python (serving and orchestration skeletons), HTML (presentation and landing page)
- **Serving:** FastAPI, Starlette, Pydantic, `prometheus_client`
- **Orchestration:** Apache Airflow
- **Reference infrastructure (compose services):** Traefik, Keycloak, PostgreSQL, MinIO, MLflow, Prometheus, Grafana, Loki, Docker Compose

Note: the Python dependencies actually declared are `airflow`, `fastapi`, `prometheus_client`, `pydantic`, `starlette`, `uuid`. MLflow, Keycloak, MinIO, and the monitoring stack appear as containerised services in the reference compose file and in the architecture docs, not as installed Python packages.

---

## Repository structure

```
.
├── architecture/
│   ├── data_flow_diagram.md
│   ├── module_integration.md
│   └── platform_architecture.md
├── infrastructure/
│   ├── airflow_dag_skeleton.py
│   ├── docker-compose.yml
│   ├── fastapi_skeleton.py
│   └── prometheus_grafana_notes.md
├── manuscripts/
│   └── manuscript.md
├── reports/
│   └── references.md
├── deliverables/
│   └── presentation.html
├── index.html
├── requirements.txt
├── LICENSE
└── NOTICE
```

---

## How to read and use

Start with the design, then the scaffolds.

1. Read the architecture and the capstone:
   - `architecture/platform_architecture.md`
   - `manuscripts/manuscript.md`
2. Review the serving contract and orchestration skeletons:
   - `infrastructure/fastapi_skeleton.py`
   - `infrastructure/airflow_dag_skeleton.py`
3. Install the declared Python dependencies if you want to import the skeletons:

```bash
git clone https://github.com/Sandyyy123/mlops-federated-learning-platform.git
cd mlops-federated-learning-platform
pip install -r requirements.txt
```

The FastAPI file exposes a `create_app(adapter)` factory rather than a ready-to-run service; a concrete `ModuleAdapter` implementation is required to build an app, and those module wrappers are intentionally not included at this stage. Example wiring, once an adapter exists:

```python
# example only, adapter not included in this repo
from infrastructure.fastapi_skeleton import create_app
# from modules.csat.wrapper import CsatAdapter
# api = create_app(CsatAdapter())
```

The `docker-compose.yml` is a reference configuration. It references per-module build contexts (for example `../modules/csat`) and environment variables (`.env`) that are not part of this repository, so it is meant to be adapted to a target environment rather than brought up unchanged.

---

## Outputs

This repository ships design and written deliverables (architecture documents, the IMRaD manuscript, a verified reference list, and an HTML presentation). It does not include trained model weights, datasets, experiment logs, or empirical benchmark numbers, and none are claimed here.

---

## Status flag

This is a **design-stage capstone**: architecture, a concrete serving contract, an orchestration skeleton, a reference infrastructure stack, and the written manuscript. The module-specific implementation (model adapters, training code, CI/CD workflows, and a live deployment) is described in the design but not implemented in this repository. Read it as a platform blueprint plus runnable scaffolding, not as a production system.

---

## Author

**Dr. Sandeep Grover** - [github.com/Sandyyy123](https://github.com/Sandyyy123)

---

## License

Proprietary, All Rights Reserved. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
