# Module Integration Contracts

This document defines, per federated module, exactly how the source project (#2,
#6, #7) plugs into the Werkstatt AI platform. The integration is contract-first:
each module exposes the same five endpoints and obeys the same request and
response schemas; only the model body differs.

## Common contract

### Request
```json
POST /predict
Authorization: Bearer <tenant JWT>
Content-Type: application/json

{
  "request_id": "uuid",
  "module": "csat | catalog | anomaly",
  "payload": { module-specific }
}
```

### Response
```json
{
  "request_id": "uuid",
  "module": "csat | catalog | anomaly",
  "model_uri": "models:/werkstatt.<module>.<name>/Production",
  "model_version": "<int>",
  "prediction": { module-specific },
  "confidence": 0.0 to 1.0,
  "tier": "1 | 2 | 3",
  "latency_ms": <int>,
  "tenant_id": "<uuid>"
}
```

### Error
HTTP 4xx for validation, 5xx for inference failures. All errors include a
`request_id` echo and a `code` field for the gateway to map to user-facing copy.

## Module A: Customer Satisfaction (source: project 02_supply_chain_csat)

**Task.** Binary classification: will the next review be 4 to 5 stars (positive) or 1 to 3 (non-positive)?

**Source artefacts to import.**
- Final tuned model from `liora_projects/02_supply_chain_csat/deliverables/model_advanced.pkl`
- Feature schema from `liora_projects/02_supply_chain_csat/src/features.py`
- Preprocessing pipeline (column transformer plus encoder) from the same file

**Werkstatt wrapping.**
- `src/wrappers/csat_wrapper.py` (Phase 2): loads the pickle, exposes `.predict_proba`, applies the same preprocessing.
- Tier 1 only (CPU). Sub-100 ms p95.
- Feature store view `online.csat_features_v1` matches the training column order exactly.

**Payload schema.**
```json
{
  "order_id": "string",
  "delivery_days": int,
  "review_lag_days": int,
  "price_eur": float,
  "freight_eur": float,
  "category_code": "string",
  "seller_id": "string"
}
```

**Prediction schema.**
```json
{
  "label": "positive | non_positive",
  "p_positive": 0.0 to 1.0
}
```

**Drift signals to monitor.**
- Distribution of `delivery_days` (most predictive feature in source project EDA).
- Class balance of predicted labels per day.
- PSI of `category_code` (categorical drift on new product lines).

## Module B: Multimodal Product Classification (source: project 06_rakuten_multimodal)

**Task.** Multi-class classification of product listings using image plus text.

**Source artefacts to import.**
- Vision branch checkpoint from `liora_projects/06_rakuten_multimodal/deliverables/vision_branch.pt`
- Text branch tokenizer and weights from the same folder
- Fusion head from `liora_projects/06_rakuten_multimodal/src/fusion.py`

**Werkstatt wrapping.**
- `src/wrappers/catalog_wrapper.py` (Phase 2): runs both branches, late-fuses logits, returns top-3 with confidences.
- Tier 2. Quantised vision branch on small GPU; falls back to Tier 1 cached prediction if the same image hash was seen in the last 24 h.
- Image upload is multipart; the gateway pre-signs an S3 URL and the inference service reads from S3.

**Payload schema.**
```json
{
  "image_s3_uri": "s3://werkstatt/uploads/...",
  "title": "string",
  "description": "string",
  "language": "fr | en | de"
}
```

**Prediction schema.**
```json
{
  "top_k": [
    {"class": "string", "confidence": 0.0 to 1.0},
    ...
  ]
}
```

**Drift signals to monitor.**
- Mean image embedding norm per day (catches camera or pipeline change).
- Top-1 confidence histogram (catches new categories not in training set).
- Language mix.

## Module C: Industrial Anomaly Detection (source: project 07_industrial_anomaly)

**Task.** Binary anomaly score per image patch, plus a per-image overall score and segmentation map.

**Source artefacts to import.**
- PaDiM or PatchCore feature memory bank from `liora_projects/07_industrial_anomaly/deliverables/memory_bank.pt`
- Backbone weights (ResNet or WideResNet) from the same folder
- Threshold from validation set saved in `liora_projects/07_industrial_anomaly/deliverables/threshold.json`

**Werkstatt wrapping.**
- `src/wrappers/anomaly_wrapper.py` (Phase 2): loads backbone, computes embedding, distance to memory bank, threshold-based decision.
- Tier 3 (full GPU). p95 target 1.5 s.
- Output includes a heatmap as a base64 PNG so the workshop UI can overlay it on the original image.

**Payload schema.**
```json
{
  "image_s3_uri": "s3://werkstatt/qc/...",
  "part_class": "string",
  "camera_id": "string"
}
```

**Prediction schema.**
```json
{
  "anomaly_score": 0.0 to 1.0,
  "label": "ok | defective",
  "heatmap_base64_png": "string"
}
```

**Drift signals to monitor.**
- Camera-level mean and std of input image brightness.
- Score distribution per part class (catches process drift in casting or stamping).
- Defect rate per shift (downstream business metric).

## Cross-module guarantees

1. **Same JWT, same tenant.** A token issued for tenant T can call any module; predictions never leak across tenants.
2. **Same feature store.** All three modules read from the same Postgres instance, only different schemas. One backup policy covers all.
3. **Same model registry stages.** No module can serve from `Staging` in production traffic; the gateway rejects calls if `model/info` returns a non-Production stage.
4. **Same logging schema.** All three modules emit the same JSON log line: `request_id`, `tenant_id`, `module`, `model_version`, `latency_ms`, `tier`, `confidence`, `outcome`. One Loki query covers all three.

## Phase 1 vs Phase 2

Phase 1 (this scaffold) defines the contracts and the skeletons. The wrapper
classes referenced above are stubs; Phase 2 fills them in by importing the
trained artefacts from projects #2, #6, and #7. No code in those source projects
is modified.
