from __future__ import annotations

import os
from pathlib import Path


def s3_key_for(run_id: str, rel_path: str, prefix: str = "runs") -> str:
    return f"{prefix}/{run_id}/{rel_path}"


def upload_run_dir(run_dir: Path, bucket: str, prefix: str = "runs") -> str:
    """Upload every file under run_dir to s3://<bucket>/<prefix>/<run_id>/...

    Endpoint + credentials come from MLFLOW_S3_ENDPOINT_URL / AWS_* env vars
    (MinIO-compatible). Returns the s3:// URI of the uploaded run folder.
    """
    import boto3

    run_dir = Path(run_dir)
    run_id = run_dir.name
    client = boto3.client("s3", endpoint_url=os.environ.get("MLFLOW_S3_ENDPOINT_URL"))
    for path in sorted(p for p in run_dir.rglob("*") if p.is_file()):
        rel = str(path.relative_to(run_dir))
        client.upload_file(str(path), bucket, s3_key_for(run_id, rel, prefix))
    return f"s3://{bucket}/{prefix}/{run_id}"
