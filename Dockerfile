FROM python:3.10-slim

WORKDIR /workspaces/MLOps-BitcoinVolatilityDetection

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY mlflow.db* ./
COPY models/ ./models/
COPY mlruns/ ./mlruns/

EXPOSE 5000

CMD ["python", "app.py"]