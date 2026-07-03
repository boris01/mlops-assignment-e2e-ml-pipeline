from pipeline.storage import s3_key_for


def test_s3_key_joins_prefix_run_and_relpath():
    assert s3_key_for("Eval_Test", "metrics.json") == "runs/Eval_Test/metrics.json"
    assert (
        s3_key_for("Eval_Test", "run-agent/preds.json")
        == "runs/Eval_Test/run-agent/preds.json"
    )


def test_s3_key_custom_prefix():
    assert s3_key_for("r1", "config.json", prefix="experiments") == "experiments/r1/config.json"
