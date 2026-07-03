# Custom Airflow image for the compose stack.
#
# The Airflow services only orchestrate: they launch the agent/eval as DockerOperator
# containers (which carry swebench + mini-swe-agent themselves) and, in summarize_and_log,
# log to MLflow and upload to S3/MinIO. So they need only: the Docker provider, a light
# MLflow client, and boto3 — NOT swebench/mini-swe-agent.
#
# The Docker provider is installed WITH Airflow's constraints so celery/kombu (CeleryExecutor)
# are not clobbered. mlflow-skinny + boto3 are light clients that don't touch celery.
FROM apache/airflow:3.0.2

RUN pip install --no-cache-dir \
      apache-airflow-providers-docker \
      --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.0.2/constraints-3.12.txt" \
 && pip install --no-cache-dir mlflow-skinny boto3
