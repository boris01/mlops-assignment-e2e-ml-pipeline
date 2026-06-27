import json
from pipeline.paths import prepare_run_dir, build_manifest, write_metrics


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


def test_write_metrics_roundtrip(tmp_path):
    run_dir = tmp_path / "run1"
    run_dir.mkdir()
    metrics = {"resolved_count": 1, "total": 3, "resolve_rate": 0.3333}
    path = write_metrics(run_dir, metrics)
    assert path == run_dir / "metrics.json"
    assert path.exists()
    assert json.loads(path.read_text()) == metrics


def test_prepare_run_dir_clears_stale_subdirs(tmp_path):
    cfg = {"run_id": "r2", "subset": "verified"}
    # First prepare
    run_dir = prepare_run_dir(cfg, runs_root=tmp_path)
    # Plant a stale file
    stale_log_dir = run_dir / "run-eval" / "logs"
    stale_log_dir.mkdir(parents=True, exist_ok=True)
    stale_file = stale_log_dir / "old.json"
    stale_file.write_text("{}")
    assert stale_file.exists()
    # Re-prepare with same cfg/runs_root
    prepare_run_dir(cfg, runs_root=tmp_path)
    assert not stale_file.exists(), "stale file should be gone after re-prepare"
    assert (run_dir / "run-eval").is_dir(), "run-eval dir should still exist"
    assert (run_dir / "run-agent").is_dir(), "run-agent dir should still exist"
