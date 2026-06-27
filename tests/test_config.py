import re
import pytest
from pipeline.config import build_run_config, DATASET_BY_SUBSET


def test_derives_dataset_and_passes_through_values():
    cfg = build_run_config({
        "split": "test", "subset": "verified", "workers": 5,
        "model": "nebius/moonshotai/Kimi-K2.6", "task_slice": "0:3",
        "run_id": "fixed-id", "cost_limit": 0, "eval_namespace": "",
    })
    assert cfg["dataset_name"] == "princeton-nlp/SWE-bench_Verified"
    assert cfg["run_id"] == "fixed-id"
    assert cfg["workers"] == 5
    assert cfg["eval_namespace"] == ""


def test_generates_run_id_when_blank():
    cfg = build_run_config({"split": "test", "subset": "lite", "workers": 1, "run_id": ""})
    assert re.match(r"\d{8}T\d{6}Z-lite-test", cfg["run_id"])
    assert cfg["dataset_name"] == "princeton-nlp/SWE-bench_Lite"


def test_unknown_subset_raises():
    with pytest.raises(ValueError):
        build_run_config({"split": "test", "subset": "bogus", "workers": 1})
