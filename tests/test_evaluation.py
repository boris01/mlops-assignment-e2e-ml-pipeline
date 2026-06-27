from pathlib import Path
from pipeline.evaluation import build_eval_command


def test_build_eval_command_uses_config_values():
    cfg = {
        "dataset_name": "princeton-nlp/SWE-bench_Verified",
        "workers": 5, "run_id": "r1", "eval_namespace": "",
    }
    cmd = build_eval_command(cfg, Path("/runs/r1/run-agent/preds.json"))
    assert cmd[:3] == ["python", "-m", "swebench.harness.run_evaluation"]
    assert "--dataset_name" in cmd and "princeton-nlp/SWE-bench_Verified" in cmd
    assert "--predictions_path" in cmd and "/runs/r1/run-agent/preds.json" in cmd
    assert "--max_workers" in cmd and "5" in cmd
    assert "--run_id" in cmd and "r1" in cmd
    assert "--namespace" in cmd  # empty string value => build locally on arm64
