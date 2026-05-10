# Data Flow Diagram

## 1. Mermaid: end-to-end request and training flow

```mermaid
flowchart LR
    subgraph Tenant
        UI[Workshop UI / API client]
    end

    subgraph ControlPlane[Werkstatt Control Plane]
        GW[Traefik API Gateway<br/>OIDC, rate limit, mTLS]
        AUTH[Keycloak]
        REG[(MLflow Registry)]
        FS[(Postgres Feature Store)]
        ORCH[Airflow Orchestrator]
        PROM[Prometheus]
        GRAF[Grafana]
    end

    subgraph Modules[Inference Plane]
        A[Module A: CSAT FastAPI<br/>Tier 1 CPU]
        B[Module B: Catalogue FastAPI<br/>Tier 2 GPU]
        C[Module C: Anomaly FastAPI<br/>Tier 3 GPU]
    end

    subgraph Storage
        S3[(MinIO Object Store<br/>images, artefacts)]
        LOG[(Loki Logs)]
    end

    UI -->|JWT| GW
    GW --> AUTH
    GW -->|/predict| A
    GW -->|/predict| B
    GW -->|/predict| C

    A --> FS
    B --> FS
    B --> S3
    C --> S3
    C --> FS

    A -->|model URI| REG
    B -->|model URI| REG
    C -->|model URI| REG

    A -->|metrics| PROM
    B -->|metrics| PROM
    C -->|metrics| PROM
    PROM --> GRAF

    A -->|json log| LOG
    B -->|json log| LOG
    C -->|json log| LOG

    ORCH -->|train, validate, register| REG
    ORCH --> FS
    ORCH --> S3

    PROM -->|drift alert| ORCH
```

## 2. Mermaid: training to deployment lifecycle

```mermaid
sequenceDiagram
    participant Air as Airflow DAG
    participant FS as Feature Store
    participant Train as Training Job
    participant Eval as Evaluation
    participant Reg as MLflow Registry
    participant Gate as API Gateway
    participant Mod as Module FastAPI

    Air->>FS: extract offline features
    FS-->>Air: training set
    Air->>Train: fit model
    Train-->>Air: model artefact
    Air->>Eval: validate on hold-out
    Eval-->>Air: metrics, pass/fail
    alt metrics pass
        Air->>Reg: register, stage Staging
        Air->>Reg: promote Staging to Production
        Reg-->>Mod: notify model version bump
        Mod->>Reg: pull new URI
        Mod-->>Gate: ready for traffic
    else metrics fail
        Air->>Air: alert, do not promote
    end
```

## 3. ASCII: data flow at request time

```
   Workshop                  Werkstatt AI
   --------                  ------------
                                                          
   [Client] --HTTPS+JWT-->  [Traefik]  --OIDC-->  [Keycloak]
                              |
                              |  routed by /api/<module>
                              v
                   +-----------+-----------+
                   |           |           |
                   v           v           v
                 [A CSAT]   [B Catalog]  [C Anomaly]
                   |           |           |
                   |           +--read-->  [MinIO S3]
                   |           |           |
                   +-----+-----+-----+-----+
                         |           |
                         v           v
                   [Postgres FS]  [MLflow Reg]
                                          
                   metrics scraped every 15 s
                              |
                              v
                        [Prometheus] -> [Grafana / Alertmanager]
```

## 4. Drift detection feedback loop

```
[Live request] --> [Module] --> [feature snapshot to Postgres]
                                       |
                                       v
                                 [PSI calculator job, hourly]
                                       |
                              PSI > 0.25 on N features
                                       |
                                       v
                              [Alertmanager -> Airflow trigger]
                                       |
                                       v
                              [Retrain DAG starts]
                                       |
                              [pass / fail logged]
                                       |
                              [auto-promote on pass]
```

## 5. Notes

- Every arrow above is in scope for v1.0 implementation. v1.0 (this
  implementation) only defines the topology.
- The drift loop is the most opinionated part of the design: it intentionally
  trades a small false-positive retraining cost for the much larger cost of a
  silently degrading model in production. References 9 to 12 in
  `reports/references.md` justify the threshold choices.
