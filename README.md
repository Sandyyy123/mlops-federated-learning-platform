![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![MLOps](https://img.shields.io/badge/MLOps-federated-purple) ![Docker](https://img.shields.io/badge/Docker-containerised-blue) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

# MLOps + Federated Learning Platform — Werkstatt AI Capstone

End-to-end MLOps platform with federated learning, model registry, CI/CD pipelines, and monitoring — production ML infrastructure capstone.

---

## Task

**MLOps / Federated Learning**

---

## Architecture

```
Federated Clients → FedAvg (Flower) → Global Model → MLflow Registry → FastAPI Serving → Monitoring
```

---

## Key Features

- Federated learning with Flower (flwr) — FedAvg aggregation across simulated clients
- MLflow experiment tracking + model registry
- FastAPI model serving endpoint with health checks
- GitHub Actions CI/CD pipeline (lint → test → build → deploy)
- Prometheus + Grafana monitoring for model drift and latency
- Privacy-preserving: no raw data leaves client nodes

---

## Dataset

Synthetic federated client datasets (privacy-preserving simulation)

---

## Project Structure

```
├── src/
│   ├── model_baseline.py      # Baseline model
│   └── model_advanced.py      # Advanced model
├── notebooks/
│   └── 01_EDA.ipynb           # Exploratory analysis
├── manuscripts/
│   └── manuscript.md          # IMRaD writeup
├── reports/
│   └── references.md          # Verified references
├── deliverables/
│   └── presentation.html      # Self-contained HTML
├── data/
│   └── README.md              # Dataset download instructions
└── requirements.txt
```

---

## Quick Start

```bash
git clone https://github.com/Sandyyy123/mlops-federated-learning-platform.git
cd mlops-federated-learning-platform
pip install -r requirements.txt

# See data/README.md for dataset download
python infrastructure/fastapi_skeleton.py  # API scaffold
python infrastructure/airflow_dag_skeleton.py  # DAG scaffold
python src/model_advanced.py
```

---

## Tech Stack

`MLflow · Flower (flwr) · FastAPI · Docker · GitHub Actions · Prometheus`

---

## Author

**Dr. Sandeep Grover** — PhD Data Science, independent ML researcher, Mössingen, Germany.

---

## License

MIT
