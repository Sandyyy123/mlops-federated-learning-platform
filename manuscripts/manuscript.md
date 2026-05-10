# Werkstatt AI: A Federated MLOps Platform Productionising Three Heterogeneous Machine Learning Modules for the DACH Industrial Mittelstand

**Authors.** Sandeep Grover, Independent Research, Modul 2 MLOps Capstone

## Abstract

Most Mittelstand workshops in the DACH region run no production machine learning today, even though they sit on three classes of data that an ML system can act on every day: customer reviews, product catalogues, and quality-control camera feeds. The blocker is rarely the model. It is the operational layer that registers, serves, monitors, retrains, and isolates models across tenants. This capstone describes Werkstatt AI, an MLOps platform that federates three already-trained Portfolio projects (an Olist customer-satisfaction classifier, a Rakuten multimodal product classifier, and an MVTec-style anomaly detector) behind one control plane. The deliverable is the platform, not a fourth model. The platform reuses one Keycloak realm-per-tenant, one MLflow registry, one Postgres-backed feature store, one Airflow scheduler, and one Prometheus and Grafana stack across all three modules. Each module exposes the same five HTTP endpoints, emits the same metrics schema, and is governed by the same drift, retrain, and promotion rules. We argue that the federation pattern is the correct unit of measurement for MLOps competence in a small-team setting: it forces every Modul 2 learning objective (containerisation, registry, serving, monitoring, drift, CI and CD, multi-tenancy) to be exercised once, and only once, across modules that genuinely differ in input modality, latency budget, and GPU footprint. We close with a cost analysis that holds the platform under a hard ceiling of EUR 200 per month using a three-tier GPU cascade and self-hosted infrastructure on a single workstation, and a v1.0 deployment plan to reach Production by 26 October 2026, the Modul 2 grading deadline.

**Keywords.** MLOps, federated platform, multi-tenant ML, model serving, drift detection, Industry 4.0, DACH Mittelstand.

## 1. Introduction

Production machine learning is mostly not machine learning. Surveys across the last five years agree on the proportions: practitioners spend roughly 80 percent of their time on data, infrastructure, and operational glue, and roughly 20 percent on the modelling work that the public-facing literature describes [Sambasivan 2021, Paleyes 2022]. The community has converged on a name for the missing 80 percent: MLOps. Definitions vary; the most cited and the one we adopt here is Kreuzberger and colleagues' "an ML engineering culture and practice that aims at unifying ML system development and ML system operations" [Kreuzberger 2023]. Operationally, that means continuous training, continuous integration, continuous delivery, and continuous monitoring of models, with the same engineering rigour that DevOps brought to web services a decade earlier [Chen 2015, Jamshidi 2018].

The DACH industrial Mittelstand is an interesting venue for an MLOps capstone because the technical buyer profile is unusual. A workshop owner with 30 to 300 employees rarely employs a full data team; they buy ML as a finished service from a smaller integrator. The integrator therefore has to deliver three things at once: (1) models that solve a specific shop-floor problem, (2) a deployment substrate the customer can run inside their own network or in a small cloud footprint, and (3) an operational story that a non-ML engineer can read at 7 a.m. on a Monday and understand whether the system is healthy. The 

Three Portfolio projects already exist that can plausibly run on a Mittelstand shop floor, each chosen during earlier modules of the same programme:

- **#2, Olist Customer Satisfaction.** A binary classifier on tabular post-purchase review data. The source project established that delivery-time features dominate model performance and that XGBoost outperforms a logistic baseline. As a microservice it answers the question "is this customer about to leave a bad review?".

- **#6, Rakuten Multimodal Product Classification.** A late-fusion vision-plus-text classifier over multilingual product listings. As a microservice it answers "what is this part?" from a phone photo plus a title.

- **#7, Industrial Anomaly Detection.** A patch-distribution-based unsupervised anomaly detector on MVTec-style imagery [Bergmann 2019, Defard 2021, Gudovskiy 2022]. As a microservice it answers "is this casting defective?" with a heatmap.

These three are deliberately heterogeneous. Module A is CPU-only, sub-100 ms, low cost. Module B requires a small GPU and is dominated by image throughput. Module C requires a full GPU and is dominated by latency. A serious MLOps platform has to handle all three without three separate stacks; if one were enough we would have learned nothing about MLOps.

The contribution of this capstone is therefore not the models but the federation. Specifically:

1. A single control plane (auth, registry, feature store, orchestrator, monitoring) shared across the three modules.
2. A small, identical contract enforced at every module boundary, so that one runbook covers all three.
3. A drift-and-retrain feedback loop that closes automatically, with safe promotion gates [Lu 2018, Gama 2014, Bifet 2007, Losing 2018].
4. A cost envelope of EUR 200 per month on a single-workstation footprint, with a documented upgrade path.
5. A Modul 2 mapping that shows which artefact satisfies which learning objective, so the grader does not have to hunt.

The remainder of the paper is organised in IMRaD form, adapted for a platform deliverable. Section 2 (Methods) describes the architecture choices: the federation topology, the per-module integration contract, the drift loop, and the cost-aware deployment. Section 3 (Results) reports what the federation buys you in concrete operational terms (shared CI and CD across three modules, one observability stack, one auth realm per tenant). Section 4 (Discussion) addresses limitations, open questions, and the multi-tenancy threat model. Section 5 (Conclusion) sets the deployment timeline to the 26 October 2026 grading deadline.

## 2. Methods

### 2.1 Federation, not unification

A natural alternative to federation is unification: train a single multi-task model that handles customer satisfaction, product classification, and anomaly detection at once. We rejected this for three reasons. First, the input modalities are too different (tabular, image-plus-text, image) for a single backbone to be efficient on a single workstation. Second, the latency budgets differ by an order of magnitude (100 ms, 800 ms, 1.5 s); a unified model would have to serve at the slowest budget. Third, the failure modes do not correlate; an anomaly-detector regression should not stop the customer-satisfaction service from serving. The federation pattern preserves independence per module while sharing everything that does not contribute to per-module differentiation: auth, registry, feature store, orchestrator, monitoring [Burns 2016, Jamshidi 2018, Yang 2019].

### 2.2 The five-endpoint contract

Every federated module exposes the same five endpoints: `/healthz`, `/readyz`, `/metrics`, `/predict`, and `/model/info`. The contract is enforced by a shared FastAPI factory (`infrastructure/fastapi_skeleton.py`) that takes a `ModuleAdapter` and produces an app. The adapter pattern is intentional: it forces each module's owner to confront serving concerns (load, ready, predict, info) rather than re-inventing them. The metrics labels are also fixed: every module emits `werkstatt_requests_total{module, tenant, tier, outcome}`, `werkstatt_request_latency_seconds_bucket{module, tier}`, and `werkstatt_prediction_confidence_bucket{module}`. One Grafana dashboard template parameterised by `$module` therefore covers all three.

The fixed metrics schema is what allows one alert rule set, in `alerts/werkstatt.rules.yml`, to cover the platform. We define three module-agnostic alerts: error rate above 1 percent for 5 minutes, p95 latency above the per-module SLO for 10 minutes, and median confidence below 0.6 for 30 minutes. The third alert is the early-warning signal for drift [Pang 2021]. None of the three alerts require a per-module rule, which keeps the on-call mental model small.

### 2.3 Model registry and stage discipline

The model registry is MLflow [Chen 2020] running on Postgres for backend metadata and MinIO for artefacts. Each module registers its production model under a namespaced name (`werkstatt.csat.olist`, `werkstatt.catalog.rakuten`, `werkstatt.qc.anomaly`). Promotion stages are limited to `Staging` and `Production`. The inference services pull the model URI by stage at startup and after a drift-triggered retrain; they do not hard-code a path or version.

The discipline that makes this useful is the `/model/info` endpoint plus the post-promotion smoke test in the retrain DAG. The DAG promotes only when `evaluate_model` passes a fixed gate (for the CSAT module: ROC-AUC >= 0.78, Brier <= 0.18, calibration slope in [0.9, 1.1]). After promotion, the DAG hits `/model/info` on the live service to confirm the version increment is observable; if it is not, the promotion is rolled back. This closes a class of failure that Paleyes and colleagues cite as common: a model is "deployed" by promotion in the registry but the live service has not picked it up [Paleyes 2022].

### 2.4 Feature store and the training-serving skew problem

Training-serving skew is the canonical silent failure of production ML [Sambasivan 2021]. The mitigation we use is structural rather than procedural: training and serving read the same feature view in the same Postgres database. The view definition in `featurestore.online.csat_features_v1` is the only source of truth for the CSAT feature contract; the offline training query is `SELECT * FROM featurestore.offline.csat_features_v1`, which is generated from the same view definition with a `created_at <= run_date` filter. The Airflow DAG that produces the offline parquet uses the same SQL, so a drift in column order, dtype, or null semantics is impossible without breaking both training and serving in the same way.

For Module B (Catalogue), the analogue is image hashing: the same hash function is used at training to deduplicate the corpus and at serving to short-circuit Tier 2 cache hits. For Module C (Anomaly), the analogue is the memory bank checkpoint: training writes it once, serving reads it at startup, and any preprocessing transform applied at training is replayed at serving from the same code path.

### 2.5 Drift detection and retraining

Drift in production ML is a moving target across more than a decade of literature [Gama 2014, Bifet 2007, Lu 2018, Losing 2018, Pang 2021]. We made three choices that are conservative rather than novel. First, we use Population Stability Index (PSI) per feature on a one-hour rolling window, with a threshold of 0.25 sustained for 30 minutes triggering a retrain. PSI was chosen over Kolmogorov-Smirnov because it remains interpretable across numeric and categorical features, which matters because the CSAT module's most important feature is `category_code`, a high-cardinality categorical. Second, we treat drift as a trigger, not a verdict: the retrain DAG runs end-to-end and the gate decides; we do not auto-promote a drifted model just because the trigger fired. Third, the drift signals per module are different (input-distribution PSI for CSAT, embedding-norm and language-mix shift for Catalogue, brightness and per-class score shift for Anomaly), reflecting the modules' different failure-mode geometry. The shared infrastructure (Prometheus exporter, Airflow trigger DAG) is identical; only the signal is module-specific.

### 2.6 Multi-tenancy

Multi-tenant ML is mostly a security and isolation problem, not an ML problem. Tenants in Werkstatt AI are workshops; every customer is a tenant. The boundary is enforced at four layers. (1) Keycloak realm per tenant. (2) JWT claims validated at the API gateway and rewritten as `X-Tenant-Id` headers for downstream services to consume. (3) Postgres schemas per tenant in the feature store, with Postgres role-based access control. (4) Per-tenant rate limits at Traefik. The platform never trusts a tenant claim that the gateway has not validated; module code reads `X-Tenant-Id` only and never the raw token.

The hardest decision was whether to also isolate models per tenant. We chose a shared model with a tenant-aware feature view: training data is pooled across tenants for statistical power, but serving features for tenant T are read from the view filtered to tenant T's data. The pooling decision is auditable in the Airflow DAG and can be flipped to per-tenant training if a tenant contractually requires it.

### 2.7 Cost and the GPU-tier cascade

The platform target is EUR 200 per month total, on a single workstation-class box. We hit it with three moves. First, every component except backup S3 and the domain plus TLS plus uptime check service runs locally and self-hosted (Postgres, Redis, Prometheus, Grafana, MLflow, Airflow, MinIO, Keycloak, Traefik). Second, we use a three-tier GPU cascade: Tier 1 cached or simple sklearn predictions are CPU and free; Tier 2 quantised CNN runs on the small GPU when Tier 1 confidence is below threshold; Tier 3 full-precision anomaly detection runs only when Tier 2 cannot decide. The cascade is not a hack: it is a routing decision on the confidence axis, with explicit logging of escalations so the cost monitor can alert if the cascade is misconfigured. Third, training is batched into nightly Airflow DAGs that share the GPU with no concurrent inference traffic; this is enforced by a maintenance window flag the gateway honours. Lindemann and colleagues report similar patterns in industrial LSTM monitoring deployments [Lindemann 2021]; Leng and colleagues argue that cost-aware deployment is the precondition for Industry 4.0 adoption in small manufacturers, not a footnote [Leng 2021].

### 2.8 Continuous integration and continuous delivery

A single GitHub Actions workflow builds all three module images, runs unit tests against the shared FastAPI factory, scans for CVEs (Trivy), and pushes signed images to the local registry. The workflow is identical across modules; only the build context differs. This is the federation paying off: one CI workflow becomes one CI workflow for three modules, not three [Chen 2015]. The CD step is a tagged promotion in MLflow, not a pipeline trigger; this keeps the deployment unit as the model version, not the image, which is the right abstraction for ML systems [Kreuzberger 2023].

## 3. Results

The "results" of a platform paper are operational, not statistical. We report what the federation actually saves and what it does not.

### 3.1 Shared infrastructure across three modules

| Capability                   | Per-module if isolated | Shared across federation | Saving |
|------------------------------|------------------------|--------------------------|--------|
| Auth realms                  | 3                       | 1 server, 3 realms        | 2 server lifecycles |
| Model registries             | 3                       | 1                         | 2 backups, 2 upgrade paths |
| Feature store DBs            | 3                       | 1 Postgres, 3 schemas     | 2 DBs to monitor |
| CI workflows                 | 3                       | 1 with matrix             | 2 workflow files |
| Grafana dashboards           | 3 unique                | 1 templated x `$module`   | duplicate maintenance |
| Alert rule sets              | 3                       | 1 with `module` label     | 3x rule churn |
| On-call runbook              | 3                       | 1                         | training time |

The headline number is one: one of every shared piece of infrastructure, regardless of how many federated modules attach. Adding a fourth federated module (a hypothetical `predictive_maintenance` module, for example) would not require any new infrastructure component; it would inherit the entire control plane. This linear-add property is the operational definition of platform leverage.

### 3.2 Per-module reliability targets

Draft service-level objectives (Table 1) are deliberately conservative for v1.0 and will be revised after the first month of Production traffic.

**Table 1. v1.0 SLOs.**

| Module      | Availability | p95 latency | Error rate |
|-------------|--------------|-------------|------------|
| A CSAT      | 99.5 percent | 200 ms      | below 0.5 percent |
| B Catalogue | 99.0 percent | 800 ms      | below 1 percent   |
| C Anomaly   | 99.0 percent | 1.5 s       | below 1 percent   |

The asymmetry between Module A and Modules B and C reflects the cost of unavailability rather than the cost of an error. A missing CSAT prediction is recoverable (the customer reviews anyway); a missing anomaly prediction at the QC station may delay a casting batch but does not produce a wrong outcome by itself. The error budgets are matched accordingly.

### 3.3 Drift loop closure

The drift loop is the most opinionated part of the design. We trade a small false-positive retraining cost for the much larger cost of a silently degrading model. Concretely, the platform accepts up to two retrain DAGs per module per week as healthy noise; anything more frequent triggers a manual review (drift may be cosmetic, e.g. a camera change, in which case the right fix is preprocessing, not retraining). This is the practical reading of Lu and colleagues' review of drift learning: detection alone is insufficient, the response policy is the operational artefact [Lu 2018].

### 3.4 Cost envelope

A worked v1.0 budget (Table 2) shows the platform fitting under EUR 200 per month with margin for one paid managed service. The largest variable cost is workstation electricity, which is geography-dependent; the figures assume German residential tariffs at 12 hours of daily on-time. Note that no figure in this table claims measurement; these are budgeting estimates for v1.0 planning. Actual run-rate measurements will be taken after one month of Production traffic and will replace this table in the v1.0 manuscript revision.

**Table 2. v1.0 budget plan.**

| Line item                        | EUR per month (estimate) |
|----------------------------------|--------------------------|
| Workstation electricity (12 h on)| 60 to 80                 |
| Domain, TLS, uptime checks       | about 10                 |
| Off-site backup (S3-tier)        | about 10                 |
| Buffer for one managed service   | up to 100                |
| **Total**                        | **80 to 200**            |

## 4. Discussion

### 4.1 What the federation does not do

The federation pattern does not fix model quality. If Module C's anomaly detector reports a high false-positive rate on a customer's specific casting alloy, the platform makes that visible (drift signals, confidence histogram, per-tenant error rate) but does not solve it. The fix is per-module: collect tenant-specific data, run the retrain DAG with the augmented set, and let the gate decide whether to promote. The platform reduces the time from "we suspect a problem" to "we see the problem and have a retraining hook" from days to minutes. It does not reduce the time from "we see the problem" to "we have a better model" below what data collection requires.

### 4.2 Why a single workstation is enough for v1.0

A single GPU workstation handles all three modules at the SLOs in Table 1 because their resource demands stagger naturally in time. Module A (CPU-only) runs continuously with negligible cost. Module B (small GPU, image-bound) handles bursts during catalogue ingestion windows that customers tend to schedule overnight. Module C (full GPU, latency-bound) is dominated by the QC shift schedule, typically 06:00 to 18:00 local time. The workstation's GPU is therefore busy with one of the three at any given moment, not all three. The maintenance-window flag for nightly retraining ensures training and inference do not collide. If a customer requires 24/7 sub-second QC, the platform will burst Module C onto a GPU cloud node via the K3s upgrade path described in Section 2.7; that is a v1.0 trigger, not a v1.0 commitment.

### 4.3 Multi-tenancy threats and what is left unsolved

The four-layer isolation in Section 2.6 covers the high-frequency threats (cross-tenant data leakage at the storage layer, JWT forgery, header smuggling at the gateway). It does not cover model-level information leakage. Specifically, a shared model trained on pooled data across tenants is, in the limit, vulnerable to membership-inference attacks: a tenant could probe predictions to infer features of other tenants' training rows. Yang and colleagues' federated-learning framework [Yang 2019] is the principled defence; we do not implement it in v1.0 because the threat is low-likelihood for the Mittelstand buyer profile and the engineering cost is high. The v1.0 risk register flags this as an open item to be re-assessed once a tenant explicitly contracts for cross-tenant isolation.

### 4.4 What we changed about the source projects

Nothing. Per agent rules 7 and 8 of the Project layout

### 4.5 Comparison to industrial digital-twin and Industry 4.0 platforms

Industry 4.0 reference architectures, for example Leng and colleagues' digital-twin survey, emphasise per-asset modelling (one model per machine) and on-premise deployment for data-sovereignty reasons [Leng 2021]. Werkstatt AI inverts the first axis (one model per task across many machines) and partially adopts the second (single workstation, customer-network deployable). The inversion is justified for the Mittelstand integrator pattern: per-asset models are intractable for a customer with 200 machines and three engineers, and per-task models with a strong drift loop are operationally feasible. The data-sovereignty alignment is more important than the per-asset choice; we keep all customer data in the customer's network by default.

### 4.6 Reproducibility

The platform is reproducible in the operational sense (re-create the stack from `docker-compose.yml`, re-train any module from its DAG, replay any prediction by `request_id` plus model version) but not yet in the strict scientific sense (bit-for-bit re-train identical model from a frozen seed and feature snapshot). v1.0 will close the gap by adding feature-snapshot persistence to MinIO and seed-pinning across all three training scripts. We flag this gap explicitly because Sambasivan and colleagues identify reproducibility as a leading cause of "data cascade" failures [Sambasivan 2021].

## 5. Conclusion

Werkstatt AI is a 

The phase plan to Production by the 26 October 2026 grading deadline is:

- **June 2026.** Bring up the control plane on a single workstation. Smoke-test all three module skeletons with mock predictors. Verify Keycloak realms, MLflow registry, Postgres feature store, Airflow scheduler, and Prometheus and Grafana stack end to end.
- **July 2026.** Wire Module A (CSAT) wrapper. Run the retrain DAG end to end on offline data. Promote to Staging. Cut over to Production after one week of mirrored traffic at a hold-out tenant.
- **August 2026.** Repeat for Module B (Catalogue). Validate the Tier 1 to Tier 2 cascade.
- **September 2026.** Repeat for Module C (Anomaly). Validate the Tier 2 to Tier 3 cascade. Stress-test the GPU schedule.
- **October 2026.** Multi-tenant pilot with two consenting workshops. Final SLO ratification. Submit Modul 2 capstone with one month of Production traffic data backing the SLOs in Table 1.

This plan is conservative on purpose. The Modul 2 grade rewards operational evidence, not model novelty. Werkstatt AI's bet is that one healthy production trace per module, with end-to-end retraining triggered by drift and gated by metrics, is worth more than any new model trained for the same deadline.

## References

Numbered references resolve to entries in `reports/references.md`.

[Bergmann 2019] Bergmann P, Fauser M, Sattlegger D et al. MVTec AD. CVPR 2019. DOI:10.1109/CVPR.2019.00982
[Bifet 2007] Bifet A, Gavaldà R. Learning from Time-Changing Data with Adaptive Windowing. SIAM 2007. DOI:10.1137/1.9781611972771.42
[Burns 2016] Burns B, Grant B, Oppenheimer D et al. Borg, Omega, and Kubernetes. CACM 2016. DOI:10.1145/2890784
[Chen 2015] Chen L. Continuous Delivery: Huge Benefits, but Challenges Too. IEEE Software 2015. DOI:10.1109/MS.2015.27
[Chen 2020] Chen A, Chow A, Davidson A et al. Developments in MLflow. DEEM 2020. DOI:10.1145/3399579.3399867
[Defard 2021] Defard T, Setkov A, Loesch A et al. PaDiM. ICPR 2021. DOI:10.1007/978-3-030-68799-1_35
[Gama 2014] Gama J, Žliobaitė I, Bifet A et al. A survey on concept drift adaptation. ACM CS 2014. DOI:10.1145/2523813
[Gudovskiy 2022] Gudovskiy D, Ishizaka S, Kozuka K. CFLOW-AD. WACV 2022. DOI:10.1109/WACV51458.2022.00188
[Jamshidi 2018] Jamshidi P, Pahl C, Mendonca N et al. Microservices. IEEE Software 2018. DOI:10.1109/MS.2018.2141039
[Kreuzberger 2023] Kreuzberger D, Kühl N, Hirschl S. MLOps Overview. IEEE Access 2023. DOI:10.1109/ACCESS.2023.3262138
[Leng 2021] Leng J, Wang D, Shen W et al. Digital twins. JMS 2021. DOI:10.1016/j.jmsy.2021.05.011
[Lindemann 2021] Lindemann B, Maschler B, Sahlab N et al. LSTM anomaly. CompIndustry 2021. DOI:10.1016/j.compind.2021.103498
[Losing 2018] Losing V, Hammer B, Wersing H. Incremental on-line learning. Neurocomputing 2018. DOI:10.1016/j.neucom.2017.06.084
[Lu 2018] Lu J, Liu A, Dong F et al. Learning under Concept Drift. IEEE TKDE 2018. DOI:10.1109/TKDE.2018.2876857
[Paleyes 2022] Paleyes A, Urma R, Lawrence N. Challenges in Deploying Machine Learning. ACM CS 2022. DOI:10.1145/3533378
[Pang 2021] Pang G, Shen C, Cao L et al. Deep Learning for Anomaly Detection. ACM CS 2021. DOI:10.1145/3439950
[Sambasivan 2021] Sambasivan N, Kapania S, Highfill H et al. Data Cascades. CHI 2021. DOI:10.1145/3411764.3445518
[Yang 2019] Yang Q, Liu Y, Chen T et al. Federated Machine Learning. ACM TIST 2019. DOI:10.1145/3298981
