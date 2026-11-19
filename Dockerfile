FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /workspaces/MLOps-BitcoinVolatilityDetection

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY models/ ./models/
COPY mlruns/ ./mlruns/
RUN mkdir -p ./mlflow_store
COPY mlflow.db* ./mlflow_store/

EXPOSE 5000

CMD ["python", "app.py"]