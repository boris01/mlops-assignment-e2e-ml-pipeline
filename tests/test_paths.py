import json
from pipeline.paths import prepare_run_dir, build_manifest


def test_prepare_run_dir_creates_tree_and_config(tmp_path):
    cfg = {"run_id": "r1", "subset": "verified"}
    run_dir = prepare_run_dir(cfg, runs_root=tmp_path)
    assert (run_dir / "run-agent").is_dir()
    assert (run_dir / "run-eval").is_dir()
    assert json.loads((run_dir / "config.json").read_text())["run_id"] == "r1"


def test_build_manifest_points_to_existing_files(tmp_path):
    cfg = {"run_id": "r1"}
    run_dir = prepare_run_dir(cfg, runs_root=tmp_path)
    (run_dir / "run-agent" / "preds.json").write_text("{}")
    (run_dir / "metrics.json").write_text("{}")
    manifest = build_manifest(run_dir, {"resolved_count": 1, "total": 1, "resolve_rate": 1.0}, "s3://b/r1")
    assert manifest["artifact_uri"] == "s3://b/r1"
    assert manifest["files"]["preds"] == "run-agent/preds.json"
    assert manifest["files"]["trajectories"] is None  # not created
    assert manifest["metrics_summary"]["resolved_count"] == 1
    assert (run_dir / "manifest.json").exists()
