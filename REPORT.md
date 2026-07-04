# Report: Configurable Airflow Evaluation Pipeline for Coding-Agent Experiments

Turns the ad-hoc `scripts/*.sh` into a configurable, reproducible Airflow pipeline that runs
mini-swe-agent on a SWE-bench subset, evaluates the patches, writes a structured run folder, and
logs the run to MLflow.

## Architecture

One Airflow DAG, `evaluate_agent` (`dags/evaluate_agent.py`), with four TaskFlow tasks in a
linear chain:

```
prepare_run -> run_agent -> run_eval -> summarize_and_log
```

The DAG is thin orchestration only; all logic lives in a unit-tested `pipeline/` package so it can
be tested without Airflow and reused across deployment styles.

| Task | Calls | Produces |
|---|---|---|
| `prepare_run` | `build_run_config`, `prepare_run_dir` | `runs/<run-id>/config.json` + empty `run-agent/`, `run-eval/` |
| `run_agent` | `run_agent_batch` | trajectories + `preds.json` under `run-agent/` |
| `run_eval` | `run_swebench_eval` | SWE-bench logs + reports under `run-eval/` |
| `summarize_and_log` | `collect_metrics`, `write_metrics`, `build_manifest`, `log_mlflow_run` | `metrics.json`, `manifest.json`, MLflow run |

`pipeline/` modules: `config.py` (resolve params, derive dataset), `paths.py` (run dir, manifest,
metrics write), `agent.py` (mini-swe-agent command + runner), `evaluation.py` (SWE-bench command +
runner + output collection), `metrics.py` (parse reports), `tracking.py` (MLflow), `storage.py`
(S3/MinIO upload). A second DAG, `evaluate_agent_docker`, runs the same steps via `DockerOperator`
for the production-style deployment (see below).

The DAG, helper signatures (`build_run_config`, `prepare_run_dir`, `run_agent_batch`,
`run_swebench_eval`, `collect_metrics`, `log_mlflow_run`), and task names follow the README's
"Suggested Implementation Path" verbatim.

## How to trigger the DAG

Prerequisites: Docker running, `NEBIUS_API_KEY` in the environment, `uv` installed, and the
**mini-swe-agent repo cloned as a sibling** of this repo:

```bash
cd ..
git clone https://github.com/SWE-agent/mini-swe-agent.git
git clone https://github.com/swe-bench/SWE-bench.git   # reference
cd mlops-assignment-e2e-ml-pipeline
uv sync
```

Start Airflow (standalone) and MLflow from a shell where `NEBIUS_API_KEY` is set:

```bash
export MLFLOW_TRACKING_URI="file://$(pwd)/mlruns"   # optional; for the MLflow UI
export MLFLOW_ALLOW_FILE_STORE=true
uv run mlflow server --backend-store-uri file://$(pwd)/mlruns &   # optional UI at :5000
bash run-airflow-standalone.sh                                    # admin/admin at :8080
```

In the Airflow UI, open **`evaluate_agent`** -> **Trigger DAG w/ config**, e.g.:

```json
{"task_slice": "0:1", "workers": 1}
```

Parameters (all configurable from the trigger form; no hard-coded experiment values):

| Param | Required | Default | Notes |
|---|---|---|---|
| `split` | yes | `test` | SWE-bench split |
| `subset` | yes | `verified` | `verified` / `lite` / `full`; `dataset_name` is derived from it |
| `workers` | yes | `5` | parallelism for agent + eval |
| `model` | no | `nebius/moonshotai/Kimi-K2.6` | any litellm/Nebius model id |
| `task_slice` | no | `0:3` | instance slice (keep tiny while iterating) |
| `run_id` | no | timestamp | folder + MLflow run name; pass explicitly to reproduce |
| `cost_limit` | no | `0` | provenance only (the agent config carries the real cap) |
| `eval_namespace` | no | `""` (empty) | empty = build eval images locally (arm64); `swebench` = pull prebuilt (amd64) |
| `agent_config` | no | sibling clone path | mini-swe-agent benchmark config; override to point elsewhere |

## Artifact layout

Every run writes a self-contained, zippable tree:

```
runs/<run-id>/
  config.json        # fully-resolved config (provenance)
  run-agent/
    preds.json
    <instance_id>/<instance_id>.traj.json   # mini-swe-agent trajectory
    minisweagent.log
  run-eval/
    logs/<model_slug>/<instance_id>/report.json   # per-instance SWE-bench reports
    reports/<model_slug>.<run-id>.json            # harness summary
  metrics.json       # resolved_count, total, resolve_rate, per_instance
  manifest.json      # pointers to all key files + artifact_uri + metrics summary
```

`manifest.json` is the index: hand someone the `runs/<run-id>/` folder and they can reconstruct
the whole run (inputs, config, trajectories, predictions, eval logs/reports, metrics).

## MLflow tracking

`summarize_and_log` logs to the `swe-bench-eval` experiment: all params (incl. `model`,
`dataset_name`, `task_slice`, `eval_namespace`, `agent_config`), metrics (`resolved_count`,
`total`, `resolve_rate`), the `run_id` as the run name, and the artifact path as a tag. MLflow
logging is wrapped log-and-continue, so a tracking outage never destroys a completed run folder.
Multiple runs are therefore directly comparable in the MLflow UI.

> Screenshots: `screenshots/airflow_dag.png`, `screenshots/mlflow_runs.png` (add after a UI run).

## Completed run (committed sample)

The production-style `evaluate_agent_docker` DAG, triggered on the amd64 VM; all four tasks green.

- **run_id:** `20260703T153113Z-verified-test` — committed under `runs/` as the reproducible sample
- **config:** `subset=verified`, `split=test`, `workers=1`, `task_slice=0:1`,
  `model=nebius/moonshotai/Kimi-K2.6`, `eval_namespace=swebench` (amd64 prebuilt eval images)
- **instance:** `astropy__astropy-12907`
- **result:** **resolved 1 / 1** (resolve_rate 1.0) — the model's patch passed the real
  FAIL_TO_PASS + PASS_TO_PASS unit tests
- **artifacts:** complete `runs/20260703T153113Z-verified-test/` tree committed to the repo; the
  full copy is uploaded to `s3://mlops-artifacts/runs/20260703T153113Z-verified-test/` (MinIO)
- **tracking:** MLflow experiment `swe-bench-eval`, run logged with params, metrics
  (`resolve_rate=1.0`), and the `s3://` `artifact_uri` tag. The run exported from the tracking
  server is committed at `runs/20260703T153113Z-verified-test/mlflow_run.json` (params, metrics,
  `run_id`, and `artifact_uri` — the machine-readable proof of the logged run).
- **evidence:** `screenshots/airflow_dag.png`, `screenshots/mlflow_runs.png`,
  `screenshots/object_storage_artifacts.png`

An earlier standalone run (`evaluate_agent`, run_id `Eval_Test`) validated the non-Docker path on
the dev machine (arm64, local eval build).

## Reproducing / rerunning by run_id

Trigger again with an explicit `run_id` to reproduce a named run:

```json
{"run_id": "Eval_Test", "task_slice": "0:1", "workers": 1}
```

`prepare_run` clears the `run-agent/` and `run-eval/` subdirs on re-prepare, so a rerun of the
same `run_id` starts clean rather than folding stale reports into new metrics. All inputs needed
to reproduce a result are captured in that run's `config.json`.

## Notes and caveats

- **Apple Silicon (arm64):** SWE-bench's prebuilt eval images are amd64-only; arm64 support is
  experimental. We pass `--namespace ''` so eval images build locally as native arm64. The agent's
  own task container pulls the amd64 SWE-bench image and runs under emulation. Locally-built arm64
  environments can differ subtly from the canonical amd64 environments, so a small number of
  instances may resolve differently than the official leaderboard. Canonical results come from an
  amd64 VM (set `eval_namespace=swebench` there to pull prebuilt images).
- **`uv run`:** agent/eval commands are invoked via `uv run` so they resolve in the project venv
  regardless of how Airflow itself was launched (matches the provided example DAG).
- **Cost:** mini-swe-agent's cost tracker does not track Nebius spend (`MSWEA_COST_TRACKING=ignore_errors`),
  so a `$0.00` display is "untracked," not "free."
- **Disk:** SWE-bench eval needs significant free disk (~120 GB recommended) for cached images.

## Tests

`uv run pytest` — 22 unit tests covering config resolution (incl. `agent_config` default + nullable
params), run-dir/manifest/metrics, agent and eval command builders (both `uv run` and container
`runner` modes), the S3 key logic, MLflow logging (real file store), and load of both DAGs (DagBag).
Subprocess/DockerOperator paths are exercised by the live runs documented above.

## Production-Style Deployment (Phase B)

A second DAG, `evaluate_agent_docker` (`dags/evaluate_agent_docker.py`), runs the agent and
evaluation as **`DockerOperator`** tasks against the project image, deployed via **Docker
Compose** with **MLflow** and **MinIO** (S3-compatible storage). `prepare_run` and
`summarize_and_log` stay Python tasks (file + MLflow + S3 work on the Airflow side).

**Execution isolation (DockerOperator + docker-out-of-docker).** SWE-bench launches its own
Docker containers, so each task container mounts the host Docker socket and runs sibling
containers on the host daemon. To keep bind paths consistent, the host repo is mounted at the
**same absolute path** (`$HOST_PROJECT`, default `/opt/project`) inside the task container, and
`working_dir` matches. The mini-swe-agent clone is **mounted** into the agent container (not
baked into the image), and `agent_config` points at the mounted clone path — consistent with the
standalone path's use of the clone. Command builders take a `runner` argument: `uv run` for the
standalone path, empty for the container (the image already has the venv on PATH).

**Compose stack.** `docker compose` merges the official Airflow base with our committed
`docker-compose.override.yaml`, which adds:
- **MinIO** + a one-shot `minio-init` that creates `$ARTIFACT_BUCKET`,
- an **MLflow** server backed by MinIO (`docker/mlflow.Dockerfile`),
- our env (`NEBIUS_API_KEY`, `MLFLOW_*`, `AWS_*`, `ARTIFACT_BUCKET`, `HOST_PROJECT`,
  `EVALUATE_AGENT_IMAGE`) plus the project bind mount and Docker socket, injected into the
  Airflow services.

**Artifact upload.** `summarize_and_log` uploads the full `runs/<run-id>/` tree to
`s3://$ARTIFACT_BUCKET/runs/<run-id>/` via `pipeline/storage.py:upload_run_dir` and logs that
`s3://` URI to MLflow as the run's `artifact_uri` (log-and-continue, so an upload/tracking outage
never loses the local run folder).

### Deploy on the VM

The repo is self-contained: the official Airflow compose base (`docker-compose.yaml`) is vendored
and auto-merged with `docker-compose.override.yaml` — no `curl` step needed.

```bash
# repo at $HOST_PROJECT; mini-swe-agent cloned as a sibling; user in the `docker` group
cp .env.example .env
#   set NEBIUS_API_KEY, and:
#     HOST_PROJECT=$(pwd)
#     AIRFLOW_UID=$(id -u)
#     DOCKER_GID=$(getent group docker | cut -d: -f3)
docker build -t evaluate-agent:latest .                                       # DockerOperator image
docker build -f docker/airflow.Dockerfile -t evaluate-agent-airflow:latest .  # Airflow image
docker compose up -d                                                          # base + override
```
Airflow `:8080` (`airflow`/`airflow`), MLflow `:5001`, MinIO console `:9001`
(`minioadmin`/`minioadmin`). Trigger `evaluate_agent_docker` with `{"task_slice":"0:1","workers":1}`
(amd64 keeps `eval_namespace=swebench`). Verify: `runs/<run-id>/` on the host, the objects under
`mlops-artifacts/runs/<run-id>/` in MinIO, and the run (with the `s3://` artifact URI) in MLflow.

**Deployment specifics (settled during the live deploy):**
- **Custom Airflow image** (`docker/airflow.Dockerfile`, set via `AIRFLOW_IMAGE_NAME`): the Docker
  provider is installed under Airflow's constraints, plus `mlflow-skinny` + `boto3`. Installing
  these at boot via `_PIP_ADDITIONAL_REQUIREMENTS` clobbers `celery`/`kombu` and crashes the worker.
  `swebench`/`mini-swe-agent` are deliberately NOT on the Airflow side — they run in the
  DockerOperator image.
- **Docker socket access:** the worker gets `group_add: [$DOCKER_GID]` so DockerOperator can use the
  mounted socket (docker-out-of-docker).
- **PYTHONPATH:** the repo root (`$HOST_PROJECT`) is on `PYTHONPATH` so the DAGs import `pipeline`
  (the base compose only mounts `dags/`).
- **MLflow host port** is published on `5001` (host 5000 is often taken); the internal address the
  worker uses stays `mlflow:5000`.
- **MLflow allowed hosts:** MLflow >=3.5 DNS-rebinding protection needs `MLFLOW_SERVER_ALLOWED_HOSTS`
  to include the `mlflow` service name (worker) **and** `localhost:5001` (browser UI).

**Status:** verified **end-to-end on the amd64 VM** — `evaluate_agent_docker` ran all four tasks
green, launching the agent/eval as sibling containers via the mounted socket, producing the
committed sample run, its MinIO objects, and the MLflow entry (see *Completed run* + screenshots).
