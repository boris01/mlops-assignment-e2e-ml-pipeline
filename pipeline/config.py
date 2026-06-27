from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

DATASET_BY_SUBSET = {
    "verified": "princeton-nlp/SWE-bench_Verified",
    "lite": "princeton-nlp/SWE-bench_Lite",
    "full": "princeton-nlp/SWE-bench",
}


def _default_run_id(subset: str, split: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}-{subset}-{split}"


def build_run_config(params: dict[str, Any]) -> dict[str, Any]:
    subset = params["subset"]
    if subset not in DATASET_BY_SUBSET:
        raise ValueError(
            f"Unknown subset {subset!r}; expected one of {sorted(DATASET_BY_SUBSET)}"
        )
    split = params["split"]
    run_id = (params.get("run_id") or "").strip() or _default_run_id(subset, split)
    return {
        "run_id": run_id,
        "split": split,
        "subset": subset,
        "dataset_name": DATASET_BY_SUBSET[subset],
        "workers": int(params["workers"]),
        "model": params.get("model", "nebius/moonshotai/Kimi-K2.6"),
        "task_slice": params.get("task_slice", "0:3"),
        "cost_limit": int(params.get("cost_limit", 0)),
        "eval_namespace": params.get("eval_namespace", ""),
    }
