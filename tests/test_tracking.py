import mlflow
from pipeline.tracking import log_mlflow_run


def test_log_mlflow_run_writes_params_and_metrics(tmp_path, monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"file://{tmp_path}/mlruns")
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
    cfg = {
        "run_id": "r1", "split": "test", "subset": "verified",
        "dataset_name": "princeton-nlp/SWE-bench_Verified", "workers": 5,
        "model": "nebius/moonshotai/Kimi-K2.6", "task_slice": "0:3",
        "cost_limit": 0, "eval_namespace": "", "agent_config": "/clone/swebench.yaml",
    }
    metrics = {"resolved_count": 1, "total": 3, "resolve_rate": 0.3333}
    log_mlflow_run(cfg, metrics, "file:///runs/r1")

    client = mlflow.tracking.MlflowClient(tracking_uri=f"file://{tmp_path}/mlruns")
    exp = client.get_experiment_by_name("swe-bench-eval")
    runs = client.search_runs([exp.experiment_id])
    assert len(runs) == 1
    assert runs[0].data.params["subset"] == "verified"
    assert runs[0].data.metrics["total"] == 3.0
    assert runs[0].data.tags["artifact_uri"] == "file:///runs/r1"
