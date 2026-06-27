from pathlib import Path
from pipeline.agent import build_agent_command


def test_build_agent_command_uses_config_values():
    cfg = {
        "subset": "verified", "split": "test", "model": "nebius/moonshotai/Kimi-K2.6",
        "task_slice": "0:3", "workers": 5,
        "agent_config": "/clone/mini-swe-agent/src/minisweagent/config/benchmarks/swebench.yaml",
    }
    cmd = build_agent_command(cfg, Path("/runs/r1/run-agent"))
    assert cmd[:4] == ["uv", "run", "mini-extra", "swebench"]
    assert "--subset" in cmd and "verified" in cmd
    assert "--slice" in cmd and "0:3" in cmd
    assert "--workers" in cmd and "5" in cmd
    assert cmd[-2:] == ["-o", "/runs/r1/run-agent"]
    # --config points at the configured agent-config path (the mini-swe-agent clone)
    assert cmd[cmd.index("--config") + 1] == cfg["agent_config"]


def test_build_agent_command_no_runner_for_container():
    cfg = {
        "subset": "verified", "split": "test", "model": "m",
        "task_slice": "0:1", "workers": 1, "agent_config": "/cfg.yaml",
    }
    cmd = build_agent_command(cfg, Path("/runs/r1/run-agent"), runner=())
    # In the DockerOperator container the venv is on PATH, so no `uv run` prefix.
    assert cmd[:2] == ["mini-extra", "swebench"]
