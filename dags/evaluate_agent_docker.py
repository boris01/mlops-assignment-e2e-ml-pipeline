"""Production-style variant of evaluate_agent.

run_agent / run_eval execute as DockerOperator tasks against the project image.
The host repo is bind-mounted at the SAME absolute path inside the task container so
SWE-bench's docker-out-of-docker sibling containers (launched via the mounted Docker
socket) resolve paths consistently. The mini-swe-agent clone is mounted in (not baked
into the image), and agent_config points at the mounted clone path.

Guarded import: if apache-airflow-providers-docker is not installed in the parsing
environment (e.g. a bare standalone Airflow), this DAG is skipped rather than raising.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from airflow.sdk import Param, dag, task

try:
    from airflow.providers.docker.operators.docker import DockerOperator
    from docker.types import Mount

    _DOCKER_AVAILABLE = True
except ImportError:
    _DOCKER_AVAILABLE = False

from pipeline.agent import build_agent_command
from pipeline.config import build_run_config
from pipeline.evaluation import build_eval_command, collect_harness_outputs
from pipeline.metrics import collect_metrics
from pipeline.paths import RUNS_ROOT, build_manifest, prepare_run_dir, write_metrics
from pipeline.storage import upload_run_dir
from pipeline.tracking import log_mlflow_run

# Host repo path; bind-mounted identically into containers so sibling containers resolve paths.
HOST_PROJECT = os.environ.get("HOST_PROJECT", "/opt/project")
# mini-swe-agent clone on the host (sibling of the repo, per README setup).
HOST_MINISWE_AGENT = os.environ.get(
    "HOST_MINISWE_AGENT", str(Path(HOST_PROJECT).parent / "mini-swe-agent")
)
IMAGE = os.environ.get("EVALUATE_AGENT_IMAGE", "evaluate-agent:latest")

CLONE_MOUNT = "/opt/mini-swe-agent"
CONTAINER_RUNS = f"{HOST_PROJECT}/runs"
CONTAINER_AGENT_CONFIG = f"{CLONE_MOUNT}/src/minisweagent/config/benchmarks/swebench.yaml"


def _docker_kwargs(extra_mounts: list) -> dict:
    return dict(
        image=IMAGE,
        working_dir=HOST_PROJECT,
        mount_tmp_dir=False,
        auto_remove="success",
        docker_url="unix://var/run/docker.sock",
        network_mode="bridge",
        environment={
            "NEBIUS_API_KEY": os.environ.get("NEBIUS_API_KEY", ""),
            "MSWEA_COST_TRACKING": "ignore_errors",
        },
        mounts=[
            Mount(source=HOST_PROJECT, target=HOST_PROJECT, type="bind"),
            Mount(source="/var/run/docker.sock", target="/var/run/docker.sock", type="bind"),
            *extra_mounts,
        ],
    )


if _DOCKER_AVAILABLE:

    @dag(
        dag_id="evaluate_agent_docker",
        schedule=None,
        start_date=datetime(2024, 1, 1),
        catchup=False,
        params={
            "split": Param("test", type="string"),
            "subset": Param("verified", type="string", enum=["verified", "lite", "full"]),
            "workers": Param(5, type="integer"),
            "model": Param("nebius/moonshotai/Kimi-K2.6", type="string"),
            "task_slice": Param("0:3", type="string"),
            "run_id": Param("", type="string"),
            "cost_limit": Param(0, type="integer"),
            # amd64 VM: pull prebuilt eval images. Use "" on arm64 to build locally.
            "eval_namespace": Param("swebench", type=["string", "null"]),
            # Path to the mini-swe-agent benchmark config INSIDE the task container (mounted clone).
            "agent_config": Param(CONTAINER_AGENT_CONFIG, type=["string", "null"]),
        },
    )
    def evaluate_agent_docker():
        @task
        def prepare_run(**context) -> dict:
            cfg = build_run_config(dict(context["params"]))
            prepare_run_dir(cfg)
            out = f"{CONTAINER_RUNS}/{cfg['run_id']}/run-agent"
            preds = f"{out}/preds.json"
            # runner=() => bare commands; the image already has the venv on PATH.
            return {
                "cfg": cfg,
                "agent_command": build_agent_command(cfg, Path(out), runner=()),
                "eval_command": build_eval_command(cfg, Path(preds), runner=()),
            }

        @task
        def summarize_and_log(cfg: dict) -> dict:
            run_dir = RUNS_ROOT / cfg["run_id"]
            eval_dir = run_dir / "run-eval"
            # The eval container wrote harness output to the shared bind mount; collect it here.
            collect_harness_outputs(cfg, eval_dir)
            metrics = collect_metrics(eval_dir)
            write_metrics(run_dir, metrics)
            artifact_uri = str(run_dir)
            bucket = os.environ.get("ARTIFACT_BUCKET")
            if bucket:
                try:
                    artifact_uri = upload_run_dir(run_dir, bucket)
                except Exception as exc:  # upload must not lose a completed run
                    print(f"S3 upload failed (continuing): {exc}")
            build_manifest(run_dir, metrics, artifact_uri)
            try:
                log_mlflow_run(cfg, metrics, artifact_uri)
            except Exception as exc:  # tracking outage must not fail the run
                print(f"MLflow logging failed (continuing): {exc}")
            return metrics

        prep = prepare_run()

        run_agent = DockerOperator(
            task_id="run_agent",
            command=prep["agent_command"],
            **_docker_kwargs(
                [Mount(source=HOST_MINISWE_AGENT, target=CLONE_MOUNT, type="bind", read_only=True)]
            ),
        )
        run_eval = DockerOperator(
            task_id="run_eval",
            command=prep["eval_command"],
            **_docker_kwargs([]),
        )

        summary = summarize_and_log(prep["cfg"])
        run_agent >> run_eval >> summary

    evaluate_agent_docker()
