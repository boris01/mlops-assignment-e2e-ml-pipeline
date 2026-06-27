from __future__ import annotations

import os
from typing import Any


def log_mlflow_run(cfg: dict[str, Any], metrics: dict[str, Any], artifact_uri: str) -> None:
    import mlflow

    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("swe-bench-eval")
    with mlflow.start_run(run_name=cfg["run_id"]):
        mlflow.log_params({
            "run_id": cfg["run_id"],
            "split": cfg["split"],
            "subset": cfg["subset"],
            "dataset_name": cfg["dataset_name"],
            "workers": cfg["workers"],
            "model": cfg["model"],
            "task_slice": cfg["task_slice"],
            "cost_limit": cfg["cost_limit"],
            "eval_namespace": cfg["eval_namespace"],
        })
        mlflow.log_metrics({
            "resolved_count": float(metrics["resolved_count"]),
            "total": float(metrics["total"]),
            "resolve_rate": float(metrics["resolve_rate"]),
        })
        mlflow.set_tag("artifact_uri", artifact_uri)
