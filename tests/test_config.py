import re
import pytest
from pipeline.config import build_run_config, DATASET_BY_SUBSET, DEFAULT_AGENT_CONFIG


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


def test_agent_config_defaults_to_sibling_clone():
    cfg = build_run_config({"split": "test", "subset": "verified", "workers": 1})
    assert cfg["agent_config"] == DEFAULT_AGENT_CONFIG
    assert cfg["agent_config"].endswith(
        "mini-swe-agent/src/minisweagent/config/benchmarks/swebench.yaml"
    )


def test_nullable_params_coerce_to_defaults():
    # Airflow nullable params can arrive as None; must not break the command builders.
    cfg = build_run_config(
        {"split": "test", "subset": "verified", "workers": 1,
         "eval_namespace": None, "agent_config": None}
    )
    assert cfg["eval_namespace"] == ""
    assert cfg["agent_config"] == DEFAULT_AGENT_CONFIG


def test_agent_config_explicit_override():
    cfg = build_run_config(
        {"split": "test", "subset": "verified", "workers": 1, "agent_config": "/custom/cfg.yaml"}
    )
    assert cfg["agent_config"] == "/custom/cfg.yaml"
