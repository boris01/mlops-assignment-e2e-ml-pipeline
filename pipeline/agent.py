from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_agent_command(cfg: dict[str, Any], run_agent_dir: Path) -> list[str]:
    return [
        "mini-extra", "swebench",
        "--subset", cfg["subset"],
        "--split", cfg["split"],
        "--model", cfg["model"],
        "--slice", cfg["task_slice"],
        "--workers", str(cfg["workers"]),
        "--config", cfg["agent_config"],
        "-o", str(run_agent_dir),
    ]


def run_agent_batch(cfg: dict[str, Any], run_dir: Path) -> Path:
    agent_config = Path(cfg["agent_config"])
    if not agent_config.exists():
        raise FileNotFoundError(
            f"agent config not found: {agent_config}. Clone mini-swe-agent as a "
            "sibling of this repo (git clone https://github.com/SWE-agent/mini-swe-agent.git), "
            "or pass an explicit `agent_config` path."
        )
    run_agent_dir = run_dir / "run-agent"
    run_agent_dir.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "MSWEA_COST_TRACKING": "ignore_errors"}
    subprocess.run(build_agent_command(cfg, run_agent_dir), cwd=PROJECT_ROOT, env=env, check=True)
    preds_path = run_agent_dir / "preds.json"
    if not preds_path.exists():
        raise FileNotFoundError(f"agent run did not produce {preds_path}")
    return preds_path
