from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_eval_command(
    cfg: dict[str, Any], preds_path: Path, runner: tuple[str, ...] = ("uv", "run")
) -> list[str]:
    # `runner` defaults to ("uv", "run") (project venv, any Airflow launch style).
    # Pass runner=() in the DockerOperator path, where the venv is on the image PATH.
    return [
        *runner, "python", "-m", "swebench.harness.run_evaluation",
        "--dataset_name", cfg["dataset_name"],
        "--predictions_path", str(preds_path),
        "--max_workers", str(cfg["workers"]),
        "--run_id", cfg["run_id"],
        "--namespace", cfg["eval_namespace"],
    ]


def run_swebench_eval(cfg: dict[str, Any], preds_path: Path, run_dir: Path) -> Path:
    if not preds_path.exists() or not preds_path.read_text().strip():
        raise FileNotFoundError(f"predictions missing or empty: {preds_path}")
    subprocess.run(build_eval_command(cfg, preds_path), cwd=PROJECT_ROOT, check=True)
    eval_dir = run_dir / "run-eval"
    collect_harness_outputs(cfg, eval_dir)
    return eval_dir


def collect_harness_outputs(cfg: dict[str, Any], eval_dir: Path) -> None:
    """Copy the SWE-bench harness output (written under PROJECT_ROOT) into eval_dir.

    Used by the subprocess path (run_swebench_eval) and by the DockerOperator path,
    where the eval container writes the harness output to the shared bind mount and
    the worker copies it into the run folder afterward.
    """
    # Harness writes per-instance logs+reports under ./logs/run_evaluation/<run_id>/...
    logs_src = PROJECT_ROOT / "logs" / "run_evaluation" / cfg["run_id"]
    logs_dst = eval_dir / "logs"
    if logs_src.exists():
        if logs_dst.exists():
            shutil.rmtree(logs_dst)
        shutil.copytree(logs_src, logs_dst)
    # Harness writes a summary report <model_slug>.<run_id>.json in the cwd.
    reports_dst = eval_dir / "reports"
    reports_dst.mkdir(parents=True, exist_ok=True)
    model_slug = cfg["model"].replace("/", "__")
    summary = PROJECT_ROOT / f"{model_slug}.{cfg['run_id']}.json"
    if summary.exists():
        shutil.copy(summary, reports_dst / summary.name)
