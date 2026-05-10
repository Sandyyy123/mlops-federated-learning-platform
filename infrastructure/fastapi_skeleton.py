"""FastAPI inference skeleton for any Werkstatt AI module.

v1.0 deliverable. Skeleton only. Not executed during implementation.

The same file is used for all three federated modules. The module body
(model load, predict, drift hooks) is injected via a wrapper that
implements the `ModuleAdapter` protocol below. Wrappers live under
`modules/<name>/wrapper.py` (v1.0).
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any, Dict, Protocol

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# ----- Logging -----

LOG = logging.getLogger("werkstatt")
LOG.setLevel(logging.INFO)

# ----- Module adapter contract -----


class ModuleAdapter(Protocol):
    """Each federated module implements this small contract."""

    name: str            # csat | catalog | anomaly
    model_uri: str       # populated at startup from MLflow registry
    model_version: str

    def load(self) -> None: ...

    def predict(self, payload: Dict[str, Any], tenant_id: str) -> Dict[str, Any]: ...

    def is_ready(self) -> bool: ...


# ----- Metrics -----

REQUESTS = Counter(
    "werkstatt_requests_total",
    "Total /predict requests",
    ["module", "tenant", "tier", "outcome"],
)
LATENCY = Histogram(
    "werkstatt_request_latency_seconds",
    "End-to-end /predict latency",
    ["module", "tier"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
CONFIDENCE = Histogram(
    "werkstatt_prediction_confidence",
    "Prediction confidence distribution",
    ["module"],
    buckets=(0.0, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0),
)

# ----- App factory -----


def create_app(adapter: ModuleAdapter) -> FastAPI:
    api = FastAPI(
        title=f"Werkstatt AI - {adapter.name}",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
    )

    @api.on_event("startup")
    async def _startup() -> None:
        LOG.info("Loading model for module %s ...", adapter.name)
        adapter.load()
        LOG.info("Module %s ready, model URI %s, version %s",
                 adapter.name, adapter.model_uri, adapter.model_version)

    # ----- Schemas -----

    class PredictIn(BaseModel):
        request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
        module: str
        payload: Dict[str, Any]

    class PredictOut(BaseModel):
        request_id: str
        module: str
        model_uri: str
        model_version: str
        prediction: Dict[str, Any]
        confidence: float
        tier: str
        latency_ms: int
        tenant_id: str

    # ----- Endpoints -----

    @api.get("/healthz")
    def healthz() -> Dict[str, str]:
        return {"status": "ok"}

    @api.get("/readyz")
    def readyz() -> Dict[str, Any]:
        ready = adapter.is_ready()
        if not ready:
            raise HTTPException(status_code=503, detail="model not loaded")
        return {"status": "ready", "module": adapter.name}

    @api.get("/metrics")
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @api.get("/model/info")
    def model_info() -> Dict[str, str]:
        return {
            "module": adapter.name,
            "model_uri": adapter.model_uri,
            "model_version": adapter.model_version,
            "stage": os.environ.get("MODEL_STAGE", "Production"),
        }

    @api.post("/predict", response_model=PredictOut)
    def predict(
        body: PredictIn,
        request: Request,
        x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
    ) -> PredictOut:
        if body.module != adapter.name:
            raise HTTPException(status_code=400, detail=f"wrong module, expected {adapter.name}")

        start = time.perf_counter()
        try:
            result = adapter.predict(body.payload, tenant_id=x_tenant_id)
            outcome = "ok"
        except ValueError as exc:
            REQUESTS.labels(adapter.name, x_tenant_id, "1", "bad_request").inc()
            raise HTTPException(status_code=422, detail=str(exc))
        except Exception:
            REQUESTS.labels(adapter.name, x_tenant_id, "1", "error").inc()
            LOG.exception("predict failed, request_id=%s tenant=%s", body.request_id, x_tenant_id)
            raise HTTPException(status_code=500, detail="inference failure")

        elapsed = time.perf_counter() - start
        tier = result.get("tier", "1")
        confidence = float(result.get("confidence", 0.0))

        LATENCY.labels(adapter.name, tier).observe(elapsed)
        CONFIDENCE.labels(adapter.name).observe(confidence)
        REQUESTS.labels(adapter.name, x_tenant_id, tier, outcome).inc()

        LOG.info(
            'request_id=%s tenant=%s module=%s model_version=%s tier=%s '
            'latency_ms=%d confidence=%.3f outcome=%s',
            body.request_id, x_tenant_id, adapter.name, adapter.model_version,
            tier, int(elapsed * 1000), confidence, outcome,
        )

        return PredictOut(
            request_id=body.request_id,
            module=adapter.name,
            model_uri=adapter.model_uri,
            model_version=adapter.model_version,
            prediction=result["prediction"],
            confidence=confidence,
            tier=tier,
            latency_ms=int(elapsed * 1000),
            tenant_id=x_tenant_id,
        )

    return api


# ----- v1.0 entrypoint shape -----
#
# from modules.csat.wrapper import CsatAdapter
# api = create_app(CsatAdapter())
#
# In v1.0 the wrappers are intentionally absent; this file is the
# protocol those wrappers will satisfy.
