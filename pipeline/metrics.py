from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def collect_metrics(eval_dir: Path) -> dict[str, Any]:
    per_instance: dict[str, bool] = {}
    for report_path in sorted(Path(eval_dir).rglob("report.json")):
        data = json.loads(report_path.read_text())
        for instance_id, report in data.items():
            per_instance[instance_id] = bool(report.get("resolved", False))
    total = len(per_instance)
    resolved_count = sum(per_instance.values())
    return {
        "resolved_count": resolved_count,
        "total": total,
        "resolve_rate": (resolved_count / total) if total else 0.0,
        "per_instance": per_instance,
    }
