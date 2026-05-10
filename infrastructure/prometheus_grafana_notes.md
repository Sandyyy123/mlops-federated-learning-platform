# Prometheus and Grafana Notes

v1.0 reference for the Werkstatt AI monitoring stack. Skeleton only.

## 1. Prometheus configuration (`prometheus.yml`)

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 30s

scrape_configs:
  - job_name: traefik
    static_configs:
      - targets: ["traefik:8080"]

  - job_name: werkstatt-modules
    static_configs:
      - targets:
          - "module-csat:8000"
          - "module-catalog:8000"
          - "module-anomaly:8000"
    metrics_path: /metrics

  - job_name: mlflow
    static_configs:
      - targets: ["mlflow:5000"]

  - job_name: airflow
    static_configs:
      - targets: ["airflow:8793"]

rule_files:
  - "alerts/werkstatt.rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]
```

## 2. Alert rules (`alerts/werkstatt.rules.yml`)

```yaml
groups:
  - name: werkstatt-slo
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(werkstatt_requests_total{outcome="error"}[5m])) by (module)
          /
          clamp_min(sum(rate(werkstatt_requests_total[5m])) by (module), 1)
          > 0.01
        for: 5m
        labels: { severity: page }
        annotations:
          summary: "Werkstatt {{ $labels.module }} error rate above 1%"
          runbook: "https://wiki.werkstatt.local/runbooks/high-error-rate"

      - alert: HighP95Latency
        expr: |
          histogram_quantile(0.95,
            sum(rate(werkstatt_request_latency_seconds_bucket[5m])) by (le, module)
          ) > on(module) group_left()
          ( label_replace(vector(0.2), "module", "csat", "", "")
            or label_replace(vector(0.8), "module", "catalog", "", "")
            or label_replace(vector(1.5), "module", "anomaly", "", "")
          )
        for: 10m
        labels: { severity: page }

      - alert: ConfidenceDrop
        expr: |
          histogram_quantile(0.5,
            sum(rate(werkstatt_prediction_confidence_bucket[1h])) by (le, module)
          ) < 0.6
        for: 30m
        labels: { severity: ticket }
        annotations:
          summary: "Median confidence below 0.6 for {{ $labels.module }} - check for drift"
```

## 3. Grafana dashboards

One dashboard per module, plus a platform-level overview.

### 3.1 Per-module panels (CSAT, Catalogue, Anomaly)

| Panel | Query | Notes |
|-------|-------|-------|
| Request rate | `sum(rate(werkstatt_requests_total{module="$mod"}[5m])) by (tenant)` | per-tenant stack |
| Error rate | `sum(rate(werkstatt_requests_total{module="$mod",outcome="error"}[5m])) / clamp_min(sum(rate(werkstatt_requests_total{module="$mod"}[5m])),1)` | shared with alert |
| p50 / p95 / p99 latency | `histogram_quantile(0.5/0.95/0.99, sum(rate(werkstatt_request_latency_seconds_bucket{module="$mod"}[5m])) by (le))` | three lines |
| Confidence histogram | `sum(rate(werkstatt_prediction_confidence_bucket{module="$mod"}[15m])) by (le)` | heatmap |
| Tier mix | `sum(rate(werkstatt_requests_total{module="$mod"}[5m])) by (tier)` | sanity check on cascade |

### 3.2 Platform overview

- Total requests per minute across modules.
- Error rate per module on one stat panel.
- Cost meter (electricity plus storage plus paid services), updated daily by a custom exporter.
- Drift alert table: PSI per feature, per module, last 24 h.

## 4. Drift detection job

A small Python job runs hourly (Airflow DAG `drift_psi_hourly`) and writes one
gauge per (module, feature):

```
werkstatt_feature_psi{module="csat", feature="delivery_days"} 0.12
```

Alert fires when any feature exceeds 0.25 for 30 minutes. The alert payload
includes the feature name so the on-call engineer knows which retrain DAG to
trigger. Lu et al 2018 (reference 9) is the methodology baseline; PSI is
chosen over KS because it stays interpretable across both numeric and
categorical features.

## 5. Log aggregation (Loki)

All three modules emit one JSON log line per request with the same schema (see
`fastapi_skeleton.py`). Loki ingests through Promtail. Useful queries:

```logql
{ job="werkstatt", module="csat" } |= "outcome=error"
{ job="werkstatt" } | json | tenant="acme-gmbh" | latency_ms > 1000
```

## 6. Backup and retention

- Prometheus TSDB retention: 30 days local, 365 days remote-write to a
  cheap-tier S3 bucket.
- Grafana state in Postgres, nightly dump.
- Alertmanager silence ledger: 90 days, audited weekly.
