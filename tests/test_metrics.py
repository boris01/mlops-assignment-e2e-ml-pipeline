from pathlib import Path
from pipeline.metrics import collect_metrics

SAMPLE_EVAL_DIR = Path(__file__).resolve().parents[1] / "sample" / "logs" / "run_evaluation" / "test"


def test_collect_metrics_counts_resolved_from_sample():
    metrics = collect_metrics(SAMPLE_EVAL_DIR)
    assert metrics["total"] == 3  # three astropy instances in the sample
    assert metrics["resolved_count"] >= 1
    assert 0.0 <= metrics["resolve_rate"] <= 1.0
    assert metrics["per_instance"]["astropy__astropy-12907"] is True


def test_collect_metrics_empty_dir(tmp_path):
    metrics = collect_metrics(tmp_path)
    assert metrics == {"resolved_count": 0, "total": 0, "resolve_rate": 0.0, "per_instance": {}}
