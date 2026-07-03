from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOT = PROJECT_ROOT / "runs"


def prepare_run_dir(cfg: dict[str, Any], runs_root: Path = RUNS_ROOT) -> Path:
    run_dir = runs_root / cfg["run_id"]
    run_dir.mkdir(parents=True, exist_ok=True)
    for subdir_name in ("run-agent", "run-eval"):
        subdir = run_dir / subdir_name
        if subdir.exists():
            shutil.rmtree(subdir)
        subdir.mkdir()
    (run_dir / "config.json").write_text(json.dumps(cfg, indent=2, sort_keys=True))
    return run_dir


def write_metrics(run_dir: Path, metrics: dict[str, Any]) -> Path:
    metrics_path = run_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True))
    return metrics_path


def build_manifest(run_dir: Path, metrics: dict[str, Any], artifact_uri: str) -> dict[str, Any]:
    def rel(p: Path):
        return str(p.relative_to(run_dir)) if p.exists() else None

    # mini-swe-agent writes trajectories as run-agent/<instance_id>/<instance_id>.traj.json
    traj_files = sorted(
        str(p.relative_to(run_dir)) for p in (run_dir / "run-agent").rglob("*.traj.json")
    )

    manifest = {
        "run_id": run_dir.name,
        "artifact_uri": artifact_uri,
        "files": {
            "config": rel(run_dir / "config.json"),
            "preds": rel(run_dir / "run-agent" / "preds.json"),
            "trajectories": traj_files or None,
            "eval_logs": rel(run_dir / "run-eval" / "logs"),
            "eval_reports": rel(run_dir / "run-eval" / "reports"),
            "metrics": rel(run_dir / "metrics.json"),
        },
        "metrics_summary": {
            k: metrics[k] for k in ("resolved_count", "total", "resolve_rate") if k in metrics
        },
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest
