from pathlib import Path
from pipeline.agent import build_agent_command


def test_build_agent_command_uses_config_values():
    cfg = {
        "subset": "verified", "split": "test", "model": "nebius/moonshotai/Kimi-K2.6",
        "task_slice": "0:3", "workers": 5,
    }
    cmd = build_agent_command(cfg, Path("/runs/r1/run-agent"))
    assert cmd[:2] == ["mini-extra", "swebench"]
    assert "--subset" in cmd and "verified" in cmd
    assert "--slice" in cmd and "0:3" in cmd
    assert "--workers" in cmd and "5" in cmd
    assert cmd[-2:] == ["-o", "/runs/r1/run-agent"]
    assert "--config" in cmd  # vendored configs/swebench.yaml
