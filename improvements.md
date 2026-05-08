# IMPROVER Report - Project #22 Werkstatt AI (Modul 2 MLOps Umbrella)

Role: B (IMPROVER). Werkstatt AI is an MLOps platform that productionises three already-trained Liora modules (#2 CSAT, #6 Rakuten multimodal, #7 industrial anomaly) behind one control plane. No standalone ML model. The brief is graded on operational MLOps competence: containerisation, registry, serving, monitoring, drift, multi-tenancy, cost, CI/CD. This review focuses on platform architecture, federation patterns, monitoring/observability, multi-tenancy, cost controls, and CI/CD for ML, per the project special-case.

---

## Top Recommendation (single highest-leverage change)

**Replace MLflow Stages (Staging / Production) with the Model Registry "alias + tag" model and pin a deterministic deployment unit per tenant.**

MLflow deprecated registry stages in v2.9 (Sep 2023) in favour of model aliases and tags; v3 has dropped them entirely. The current architecture (`platform_architecture.md` 3.2, `module_integration.md` "Cross-module guarantees" 3, retrain DAG `register_and_promote`, `/model/info` endpoint) hard-codes "Staging" and "Production" stages. By the 26 Oct 2026 deadline, this design will be running against a deprecated API at best and a removed one at worst.

Concrete next steps (HIGH priority, single sprint):

1. Replace stage transitions with `set_registered_model_alias("werkstatt.csat.olist", "production", version=N)` and a `champion`/`challenger` alias pair per module.
2. Add a `tenant_pin` tag (e.g. `tenant=acme-gmbh`) so a tenant can be pinned to a specific version while the platform default rolls forward; this is the MLflow-native answer to the per-tenant model question raised in `manuscripts/manuscript.md` 2.6.
3. Update `fastapi_skeleton.py` `/model/info` to surface the alias plus the resolved version and the tenant-pin (if any). The shape becomes `{module, alias, version, tenant_pin_for_caller}`.
4. Update the smoke-test in `airflow_dag_skeleton.py` to assert `alias=production` resolves to the new version, not that `stage=Production` matches a string.

Why this is the single most leveraged change: it unblocks the multi-tenant model-isolation discussion in 4.3 (tenants can be pinned to challenger or to an older champion without forking the registry), it survives MLflow v3, and it changes only one shared file plus the DAG plus the endpoint contract - because the federation enforces a single contract, the fix lands once and three modules inherit it.

---

## Weaknesses, gaps, and proposed improvements

### 1. CI/CD pipeline is described but not defined as code (HIGH)

**Gap.** The manuscript Section 2.8 describes "a single GitHub Actions workflow" that builds all three module images, runs unit tests, scans CVEs (Trivy), and pushes signed images. No `.github/workflows/*.yml` file exists in `infrastructure/` or anywhere in the project folder. Brief Section "Phase 1 deliverables" lists `infrastructure/` artefacts but omits any CI workflow. This is the single Modul-2 learning objective that has zero artefact.

**Improvement.** Add `infrastructure/github-actions-werkstatt.yml` (skeleton-only, matching the rest of the scaffold pattern) with three jobs: (a) `lint-and-unit` running `ruff` + `pytest` against `infrastructure/fastapi_skeleton.py` and the three planned wrappers, (b) `build-and-scan` using a matrix over `[csat, catalog, anomaly]` with `docker buildx` then `aquasecurity/trivy-action@master` failing on `CRITICAL,HIGH`, (c) `register-and-tag` calling MLflow REST to set the `challenger` alias on push to `main`. Also add SBOM generation (`anchore/sbom-action`) because Trivy alone misses Python-package provenance issues.

### 2. SLO definitions are aspirational, not measurable (HIGH)

**Gap.** `platform_architecture.md` Section 8 and manuscript Table 1 define availability targets ("99.5 percent", "99.0 percent") but no error budget burn-rate alerts, no multi-window multi-burn-rate (MWMBR) configuration, and no PromQL for measuring availability itself. Without burn-rate alerts the platform will either page on every blip or miss slow-degradation outages - both documented in Google's SRE Workbook chapter 5.

**Improvement.** Replace the single `HighErrorRate` alert in `prometheus_grafana_notes.md` with a Google-style multi-window multi-burn-rate alert pair: a 1h window at 14.4x burn rate (page) and a 6h window at 6x (page), plus a 3d window at 1x (ticket). Define availability as `1 - (errors[5m]/total[5m])` and budget as `1 - SLO`. Add an "error budget remaining" Grafana stat panel per module. Total addition: ~15 lines of YAML, one Grafana panel JSON. Reference: Beyer et al, Site Reliability Workbook 2018, ch 5; also Sridharan, Distributed Systems Observability 2018, O'Reilly.

### 3. Cost controls have no enforcement mechanism (HIGH)

**Gap.** The EUR 200/month ceiling is a budgeting target with no real-time observation. `prometheus_grafana_notes.md` Section 3.2 mentions a "cost meter ... updated daily by a custom exporter" but no exporter is defined. The GPU-tier cascade is described as a routing strategy but the router and its confidence threshold are not in `fastapi_skeleton.py`. There is no `werkstatt_cost_eur_total` metric, no cost-per-tenant breakdown, and no per-tenant rate limit defined in Traefik config (Section 2.6 mentions per-tenant rate limits but `docker-compose.yml` has no Traefik dynamic config).

**Improvement.** Add three concrete pieces: (a) a `cost_exporter` skeleton service in `docker-compose.yml` that exposes `werkstatt_cost_eur_total{component}` and `werkstatt_gpu_seconds_total{module, tenant}` (use `nvidia-dcgm-exporter` as the GPU source); (b) a `traefik_dynamic.yml` snippet pinning per-tenant rate limits via Traefik's middleware (the `RateLimit` middleware indexed by the `X-Tenant-Id` header); (c) a `Tier-Router` class in `fastapi_skeleton.py` with an explicit confidence threshold (default 0.7) and a `werkstatt_tier_escalations_total{from, to, module}` counter - the cost cascade is currently invisible in the metrics schema. Add an Alertmanager rule firing when `predict_linear(werkstatt_cost_eur_total[7d], 30 * 86400) > 200`.

### 4. Multi-tenancy threat model omits secret rotation, audit log, and the data-residency story (MEDIUM)

**Gap.** `platform_architecture.md` 3.1 and 7 describe four-layer isolation (Keycloak realm, JWT validation, Postgres schemas, Traefik rate limit) but the threat model in manuscript 4.3 stops at membership inference. Three high-frequency Mittelstand-buyer concerns are unaddressed: (i) JWT key rotation strategy (current Vault dev-mode reference is a punt), (ii) per-tenant audit log retention (GDPR Art. 30 requires demonstrable processing records, not just Loki retention), (iii) data-residency proof for tenant data that never crosses the German border. The manuscript's claim of "customer-network deployable" needs an enforcement story.

**Improvement.** Add an `architecture/multitenancy_threat_model.md` covering: (a) Keycloak realm key rotation via `kc.sh export` plus a quarterly Airflow DAG, (b) per-tenant audit log retention rule in Loki using `{tenant="X"}` retention overrides, (c) a `tenant_residency` label on every metric and log line, with `region=de` enforced at ingest. For the membership-inference concern flagged in 4.3, add a per-module `dp_noise_sigma` config field (initially 0, opt-in per tenant contract) so the discussion has a concrete config knob, not just a literature reference. Reference: Carlini et al 2022, "Membership Inference Attacks From First Principles" (USENIX Security 2022); Shokri et al 2017 (S&P) for the original framework.

### 5. Drift detection uses only PSI; no embedding drift, no prediction drift, no label-delay handling (MEDIUM)

**Gap.** `platform_architecture.md` 3.5 and `prometheus_grafana_notes.md` 4 use PSI per feature with a fixed 0.25 threshold. PSI is appropriate for the CSAT module's low-cardinality numeric features but is structurally weak for: (i) Module B image embeddings (high-dimensional, where PSI is a known under-performer - see Rabanser et al 2019), (ii) Module C anomaly scores, where the score distribution itself is the drift signal and the input distribution is uninformative. The modules also have very different label-delay characteristics (CSAT label arrives within days; anomaly ground truth requires manual QC verification, often weeks), and the retrain DAG treats drift as the only trigger.

**Improvement.** Adopt a tiered drift methodology stated explicitly in `manuscripts/manuscript.md` 2.5 and reflected in the Prometheus job: (a) PSI per low-cardinality feature for CSAT, (b) MMD or two-sample KS on CLIP/timm embeddings for Catalogue, (c) Wasserstein distance on score distributions plus per-class moving median for Anomaly. Keep PSI as the unified label, just make the underlying statistic module-specific. Add a `werkstatt_label_lag_days{module}` gauge so the retrain gate can refuse to run if labels are too stale. Reference: Rabanser et al 2019, "Failing Loudly" (NeurIPS); Lipton et al 2018 BBSE for the label-shift case.

### 6. Reproducibility gap is acknowledged but no concrete plan in the scaffold (MEDIUM)

**Gap.** Manuscript 4.6 explicitly flags reproducibility as not yet bit-for-bit. The scaffold has no `requirements.txt` or `pyproject.toml` (the `infrastructure/` folder has no Python deps file), no `.python-version`, no seed-pinning convention, no DVC/MinIO snapshot policy. This is unusually exposed for a Modul-2 deliverable: every project #1-#21 has a standard `data/README.md` and reproducibility expectation.

**Improvement.** Add three small artefacts: (a) `infrastructure/requirements.txt` pinning FastAPI, MLflow client, prometheus-client, pydantic, psycopg2-binary, boto3 (for MinIO), and apache-airflow with the same versions referenced in `docker-compose.yml`; (b) an `infrastructure/seeds.md` one-pager defining the seed convention (`PYTHONHASHSEED=0`, `numpy.random.seed(42)`, `torch.manual_seed(42)`, `torch.use_deterministic_algorithms(True)` with the cudnn caveat); (c) a `infrastructure/snapshot_policy.md` defining the rule "every Airflow DAG pinned to a feature-snapshot S3 path containing `<module>/<run_id>.parquet` and the snapshot is immutable for 365 days". These add ~50 lines total and close the gap manuscript 4.6 flags.

### 7. Federation contract is stated five-endpoint but lacks contract-test enforcement (MEDIUM)

**Gap.** `module_integration.md` defines a contract; `fastapi_skeleton.py` provides a factory. Nothing asserts that Phase-2 wrappers satisfy the contract. A wrapper could silently drop `confidence` from its return dict, fail to label metrics with `tier`, or break the response schema, and there is no failing test until Production runtime. The platform's central design claim ("one runbook, one dashboard, one alert") rests on contract conformance that is currently a code-review obligation.

**Improvement.** Add `infrastructure/contract_tests.py` (skeleton, pytest) with three test classes: `TestSchemaConformance` (Pydantic model parses every wrapper's output), `TestMetricsLabels` (exposed metrics include all four required label sets), `TestEndpointSet` (`/healthz`, `/readyz`, `/metrics`, `/predict`, `/model/info` all return non-5xx). The CI workflow from improvement 1 runs these against every module image with a mock adapter. This is the operational definition of "the federation contract is enforced", not just declared.

### 8. Observability is metric-heavy but trace-light; no OpenTelemetry, no exemplars (MEDIUM)

**Gap.** The monitoring stack covers metrics (Prometheus), logs (Loki), but not traces. For a multi-module platform where a single tenant request touches the gateway, JWT validation, the model server, the feature store, and MLflow, the absence of distributed tracing means slow-request debugging requires log correlation by `request_id` across multiple services. This is feasible at low traffic but breaks at scale and is the canonical reason teams add tracing post-incident rather than pre-incident.

**Improvement.** Adopt OpenTelemetry as the unified observability standard in Phase 1: (a) add `otel-collector` to `docker-compose.yml` with `tempo` (Grafana Tempo, fits the ceiling) as the storage backend; (b) instrument `fastapi_skeleton.py` with `opentelemetry-instrumentation-fastapi` (one decorator); (c) emit Prometheus histogram exemplars linking `werkstatt_request_latency_seconds` buckets to traces - this lets a Grafana panel jump from a slow p99 directly to the offending trace. Reference: OpenTelemetry Specification 1.30+, exemplars supported since Prometheus 2.43. Adds one container, ~10 lines of FastAPI instrumentation, no API-shape change.

---

## Priority summary

| # | Improvement | Priority |
|---|-------------|----------|
| Top | MLflow alias + tenant_pin tag (replaces stages) | HIGH |
| 1 | GitHub Actions workflow as code with Trivy and SBOM | HIGH |
| 2 | Multi-window multi-burn-rate SLO alerts | HIGH |
| 3 | Cost exporter, tier-router, Traefik rate-limit config | HIGH |
| 4 | Threat model: key rotation, audit retention, residency | MEDIUM |
| 5 | Tiered drift (PSI + MMD + Wasserstein); label-lag gauge | MEDIUM |
| 6 | requirements.txt, seeds.md, snapshot_policy.md | MEDIUM |
| 7 | Contract tests in CI | MEDIUM |
| 8 | OpenTelemetry traces with exemplars | MEDIUM |

No LOW-priority items; the scaffold is dense and every improvement above lands on a Modul-2 learning objective the grader will evaluate. None of these recommendations modify the existing files; all propose additive artefacts the Phase-2 implementation can land before the 26 October 2026 deadline.
