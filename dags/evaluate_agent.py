from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# Make the project root importable so `pipeline` resolves inside Airflow.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from airflow.sdk import dag, task, Param

from pipeline.agent import run_agent_batch
from pipeline.config import build_run_config
from pipeline.evaluation import run_swebench_eval
from pipeline.metrics import collect_metrics
from pipeline.paths import RUNS_ROOT, build_manifest, prepare_run_dir, write_metrics
from pipeline.tracking import log_mlflow_run


@dag(
    dag_id="evaluate_agent",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    params={
        "split": Param("test", type="string"),
        "subset": Param("verified", type="string", enum=["verified", "lite", "full"]),
        "workers": Param(5, type="integer"),
        "model": Param("nebius/moonshotai/Kimi-K2.6", type="string"),
        "task_slice": Param("0:3", type="string"),
        "run_id": Param("", type="string"),
        "cost_limit": Param(0, type="integer"),
        # type includes "null" so the trigger form treats these as optional (empty allowed).
        # Empty eval_namespace => build eval images locally (arm64).
        "eval_namespace": Param("", type=["string", "null"]),
        # Empty agent_config => default to the sibling mini-swe-agent clone (see pipeline/config.py).
        "agent_config": Param("", type=["string", "null"]),
    },
)
def evaluate_agent():
    @task
    def prepare_run(**context) -> dict:
        cfg = build_run_config(dict(context["params"]))
        prepare_run_dir(cfg)
        return cfg

    @task
    def run_agent(cfg: dict) -> str:
        return str(run_agent_batch(cfg, RUNS_ROOT / cfg["run_id"]))

    @task
    def run_eval(cfg: dict, preds_path: str) -> str:
        eval_dir = run_swebench_eval(cfg, Path(preds_path), RUNS_ROOT / cfg["run_id"])
        return str(eval_dir)

    @task
    def summarize_and_log(cfg: dict, eval_dir: str) -> dict:
        run_dir = RUNS_ROOT / cfg["run_id"]
        metrics = collect_metrics(Path(eval_dir))
        write_metrics(run_dir, metrics)
        artifact_uri = str(run_dir)
        build_manifest(run_dir, metrics, artifact_uri)
        try:
            log_mlflow_run(cfg, metrics, artifact_uri)
        except Exception as exc:  # tracking outage must not destroy a completed run
            print(f"MLflow logging failed (continuing): {exc}")
        return metrics

    cfg = prepare_run()
    preds = run_agent(cfg)
    eval_dir = run_eval(cfg, preds)
    summarize_and_log(cfg, eval_dir)


evaluate_agent()
