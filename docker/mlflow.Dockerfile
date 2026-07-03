FROM python:3.12-slim
RUN pip install --no-cache-dir "mlflow>=2.16" "boto3>=1.34"
