"""Airflow DAG skeleton for the Werkstatt AI Customer Satisfaction module.

Phase 1 deliverable. Skeleton only. Not executed during scaffold.

Pattern repeats for the catalogue and anomaly modules - identical task
structure, different extract / train / register operators.

Schedule: weekly Monday 03:00 UTC.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

DEFAULT_ARGS = {
    "owner": "werkstatt-mlops",
    "depends_on_past": False,
    "email_on_failure": True,
    "email": ["mlops@werkstatt.local"],
    "retries": 1,
    "retry_delay": timedelta(minutes=15),
}


def extract_offline_features(**context):
    """Pull rolling 90-day window of CSAT features from offline schema.

    Reads the same SQL view definition used at serving time so training and
    serving see identical feature semantics.
    """
    # Phase 2: psycopg2 query, write parquet to MinIO under
    # s3://werkstatt-features/csat/<run_id>.parquet
    raise NotImplementedError("Phase 2 implementation")


def validate_features(**context):
    """Run TFDV-style schema and statistics validation.

    Compare current run statistics against last successful run. Fail the DAG if
    schema drifts (new column, removed column, dtype change) or if a feature's
    PSI vs reference exceeds 0.25.
    """
    raise NotImplementedError("Phase 2 implementation")


def train_model(**context):
    """Train the CSAT classifier.

    Uses the exact pipeline from project 02_supply_chain_csat. Logs all params,
    metrics, and the fitted pipeline to MLflow under experiment
    `werkstatt.csat.weekly`.
    """
    raise NotImplementedError("Phase 2 implementation")


def evaluate_model(**context):
    """Hold-out evaluation, gate on minimum metrics.

    Gate: ROC-AUC >= 0.78, Brier <= 0.18, calibration slope in [0.9, 1.1].
    Returns 'pass' or 'fail' to XCom for the branch operator downstream.
    """
    raise NotImplementedError("Phase 2 implementation")


def register_and_promote(**context):
    """Register the run as a new model version and promote to Production.

    Uses MLflow Model Registry API. Promotion is conditional on the gate result
    from `evaluate_model`. Notifies the inference service via a Pub/Sub topic so
    it pulls the new URI without a restart.
    """
    raise NotImplementedError("Phase 2 implementation")


def notify_drift_resolved(**context):
    """If this DAG was triggered by a drift alert, mark the alert resolved."""
    raise NotImplementedError("Phase 2 implementation")


with DAG(
    dag_id="csat_retrain_weekly",
    description="Werkstatt AI - retrain Customer Satisfaction module weekly",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 5, 1),
    schedule="0 3 * * 1",  # weekly Monday 03:00 UTC
    catchup=False,
    max_active_runs=1,
    tags=["werkstatt", "csat", "module_a", "mlops"],
) as dag:

    extract = PythonOperator(
        task_id="extract_offline_features",
        python_callable=extract_offline_features,
    )

    validate = PythonOperator(
        task_id="validate_features",
        python_callable=validate_features,
    )

    train = PythonOperator(
        task_id="train_model",
        python_callable=train_model,
    )

    evaluate = PythonOperator(
        task_id="evaluate_model",
        python_callable=evaluate_model,
    )

    register = PythonOperator(
        task_id="register_and_promote",
        python_callable=register_and_promote,
    )

    drift_resolved = PythonOperator(
        task_id="notify_drift_resolved",
        python_callable=notify_drift_resolved,
        trigger_rule="none_failed",
    )

    smoke_test = BashOperator(
        task_id="post_promote_smoke_test",
        bash_command=(
            "curl -fsS http://module-csat:8000/readyz && "
            "curl -fsS http://module-csat:8000/model/info"
        ),
    )

    extract >> validate >> train >> evaluate >> register >> smoke_test >> drift_resolved
