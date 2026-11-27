import os
import time
import json
from collections import deque
import numpy as np
import pandas as pd
import skops.io as sio
import mlflow
import mlflow.pyfunc
import mlflow.sklearn
from mlflow.tracking import MlflowClient
from flask import Flask, request, jsonify, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

app = Flask(__name__)

MODEL_NAME = os.getenv("MODEL_NAME", "BitcoinVolatilityDetector")
STAGE = os.getenv("STAGE", "Production")
DAGSHUB_STAGE = os.getenv("DAGSHUB_STAGE", "Staging")
METADATA_PATH = os.getenv("METADATA_PATH", "models/metadata/model_metadata.json")
MODEL_SKOPS_PATH = os.getenv("MODEL_PATH", "models/model.skops")
FALLBACK_RUN_PATH = "mlruns/1/models/m-9099abb51028425ebef7f3f4634748d8/artifacts"

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")
DAGSHUB_MLFLOW_URI = os.getenv(
    "DAGSHUB_MLFLOW_URI",
    "https://dagshub.com/lipkusuma/MLOps-BitcoinVolatilityDetection.mlflow",
)

if TRACKING_URI:
    mlflow.set_tracking_uri(TRACKING_URI)
elif os.path.exists("mlflow.db"):
    mlflow.set_tracking_uri("sqlite:///mlflow.db")

metadata = {}
model = None
model_source = "none"

if os.path.exists(METADATA_PATH):
    with open(METADATA_PATH, "r") as f:
        metadata = json.load(f)

# 1. Utama: Muat dari MLflow Model Registry
try:
    model_uri = f"models:/{MODEL_NAME}/{STAGE}"
    model = mlflow.pyfunc.load_model(model_uri)
    model_source = f"MLflow Model Registry ({model_uri})"
    print(f"✅ Model dimuat dari MLflow Registry: {model_uri}", flush=True)
except Exception as e:
    print(f"⚠️ MLflow Registry belum terjangkau langsung, cek fallback: {e}", flush=True)

# 2. Fallback Cloud Remote: DagsHub Model Registry
if model is None and os.getenv("DAGSHUB_TOKEN"):
    try:
        os.environ["MLFLOW_TRACKING_USERNAME"] = os.getenv("DAGSHUB_REPO_OWNER", "lipkusuma")
        os.environ["MLFLOW_TRACKING_PASSWORD"] = os.getenv("DAGSHUB_TOKEN", "")
        mlflow.set_tracking_uri(DAGSHUB_MLFLOW_URI)
        dagshub_uri = f"models:/{MODEL_NAME}/{DAGSHUB_STAGE}"
        model = mlflow.pyfunc.load_model(dagshub_uri)
        model_source = f"DagsHub Cloud Registry ({dagshub_uri})"
        print(f"✅ Model dimuat dari DagsHub Cloud Registry: {dagshub_uri}", flush=True)
    except Exception as e:
        print(f"⚠️ DagsHub Registry load error: {e}", flush=True)
    finally:
        if TRACKING_URI:
            mlflow.set_tracking_uri(TRACKING_URI)

# 3. Fallback Lokal: Artifact Path MLruns (Production Artifact)
if model is None:
    try:
        if os.path.exists(FALLBACK_RUN_PATH):
            model = mlflow.pyfunc.load_model(FALLBACK_RUN_PATH)
            model_source = f"MLflow Production Artifact ({FALLBACK_RUN_PATH})"
            print(f"✅ Model dimuat dari Artifact Path: {FALLBACK_RUN_PATH}", flush=True)
    except Exception as e:
        print(f"⚠️ Artifact path load error: {e}", flush=True)

# 4. Fallback Biner: File Skops Lokal
if model is None:
    try:
        if os.path.exists(MODEL_SKOPS_PATH):
            untrusted = sio.get_untrusted_types(file=MODEL_SKOPS_PATH)
            skops_m = sio.load(MODEL_SKOPS_PATH, trusted=untrusted)

            class SkopsWrapper:
                def __init__(self, m):
                    self.m = m

                def predict(self, df):
                    return self.m.predict(df)

            model = SkopsWrapper(skops_m)
            model_source = f"Local Skops Binary ({MODEL_SKOPS_PATH})"
            print(f"✅ Model dimuat dari file Skops lokal: {MODEL_SKOPS_PATH}", flush=True)
    except Exception as e:
        print(f"❌ Skops load error: {e}", flush=True)

# ==============================================================================
# PROMETHEUS METRICS INSTRUMENTATION (PILAR 1: OPERASIONAL & PILAR 2: ML / DRIFT)
# ==============================================================================
REQUEST_COUNT = Counter(
    "mlops_inference_requests_total",
    "Total permintaan inferensi yang diterima oleh layanan model",
    ["endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "mlops_inference_latency_seconds",
    "Latensi eksekusi inferensi model dalam detik",
    ["endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

PREDICTION_CLASS_COUNT = Counter(
    "mlops_predictions_total",
    "Distribusi kelas hasil prediksi model (0=Normal, 1=Anomali)",
    ["prediction_class"],
)

ANOMALY_PROBABILITY = Histogram(
    "mlops_anomaly_score",
    "Distribusi skor/probabilitas anomali volatilitas Bitcoin",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

FEATURE_SUMMARY = Summary(
    "mlops_input_feature_value",
    "Statistik ringkasan nilai fitur input untuk pemantauan Data Drift",
    ["feature"],
)

FEATURE_ROLLING_MEAN = Gauge(
    "mlops_feature_rolling_mean",
    "Rata-rata berjalan (rolling mean 50 sampel terakhir) per fitur input",
    ["feature"],
)

FEATURE_DRIFT_ZSCORE = Gauge(
    "mlops_feature_drift_zscore",
    "Skor pergeseran distribusi (Z-score shift) fitur terhadap baseline training",
    ["feature"],
)

# Baseline statistik distribusi data training normal untuk deteksi Data Drift
FEATURE_BASELINES = {
    "price": {"mean": 92000.0, "std": 3500.0},
    "volume": {"mean": 45000.0, "std": 12000.0},
    "price_change_pct": {"mean": 0.05, "std": 0.80},
    "volume_change_pct": {"mean": 1.20, "std": 0.90},
}

feature_windows = {feat: deque(maxlen=50) for feat in FEATURE_BASELINES}


def record_feature_and_prediction_metrics(df_input: pd.DataFrame, preds: list, probs: list):
    for feat, stats in FEATURE_BASELINES.items():
        if feat in df_input.columns:
            for val in df_input[feat].astype(float).tolist():
                FEATURE_SUMMARY.labels(feature=feat).observe(val)
                feature_windows[feat].append(val)
            if len(feature_windows[feat]) > 0:
                current_mean = float(np.mean(feature_windows[feat]))
                z_shift = abs(current_mean - stats["mean"]) / max(stats["std"], 1e-6)
                FEATURE_ROLLING_MEAN.labels(feature=feat).set(current_mean)
                FEATURE_DRIFT_ZSCORE.labels(feature=feat).set(round(z_shift, 4))

    for pred, prob in zip(preds, probs):
        label = "1_anomaly" if int(pred) == 1 else "0_normal"
        PREDICTION_CLASS_COUNT.labels(prediction_class=label).inc()
        ANOMALY_PROBABILITY.observe(float(prob))


def run_model_inference(df_input: pd.DataFrame):
    expected_features = ["price", "volume", "price_change_pct", "volume_change_pct"]
    missing_cols = [col for col in expected_features if col not in df_input.columns]
    if missing_cols:
        raise ValueError(f"Fitur berikut kurang: {missing_cols}")

    df_ordered = df_input[expected_features]
    preds = model.predict(df_ordered).tolist()

    # Ekstrak probabilitas kelas anomali jika model mendukung predict_proba
    probs = [float(p) for p in preds]
    try:
        raw_impl = getattr(model, "_model_impl", None)
        sk_estimator = getattr(raw_impl, "sklearn_model", raw_impl)
        if sk_estimator is not None and hasattr(sk_estimator, "predict_proba"):
            proba_arr = sk_estimator.predict_proba(df_ordered)
            if proba_arr.shape[1] >= 2:
                probs = [float(row[1]) for row in proba_arr]
    except Exception:
        pass

    record_feature_and_prediction_metrics(df_ordered, preds, probs)
    return preds, probs


@app.route("/", methods=["GET"])
def health_check():
    return jsonify({
        "status": "online",
        "system": "Bitcoin Volatility & Anomaly Detection API (Instrumented)",
        "model_registry": MODEL_NAME,
        "active_stage": STAGE,
        "model_source": model_source,
        "metrics_endpoint": "/metrics",
        "author": metadata.get("tags", {}).get("author", "Alif Kusuma Fauzan"),
        "nim": metadata.get("tags", {}).get("nim", "245150201111051"),
        "model_loaded": model is not None,
    }), 200


@app.route("/ping", methods=["GET"])
def ping():
    if model is None:
        return Response("Model not loaded\n", status=503)
    return Response("\n", status=200, mimetype="application/json")


@app.route("/metrics", methods=["GET"])
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/invocations", methods=["POST"])
def invocations():
    start_time = time.perf_counter()
    if model is None:
        REQUEST_COUNT.labels(endpoint="/invocations", status="500").inc()
        return jsonify({"error": "Model Production tidak siap"}), 500

    try:
        data = request.get_json()
        if not data:
            raise ValueError("Payload JSON kosong")

        if "dataframe_records" in data:
            df_input = pd.DataFrame(data["dataframe_records"])
        elif "features" in data:
            df_input = pd.DataFrame(data["features"])
        else:
            raise ValueError("Payload JSON wajib berisi 'dataframe_records' atau 'features'")

        preds, _ = run_model_inference(df_input)
        elapsed = time.perf_counter() - start_time
        REQUEST_LATENCY.labels(endpoint="/invocations").observe(elapsed)
        REQUEST_COUNT.labels(endpoint="/invocations", status="200").inc()

        return jsonify({"predictions": [int(p) for p in preds]}), 200

    except Exception as e:
        elapsed = time.perf_counter() - start_time
        REQUEST_LATENCY.labels(endpoint="/invocations").observe(elapsed)
        REQUEST_COUNT.labels(endpoint="/invocations", status="400").inc()
        return jsonify({"error": str(e)}), 400


@app.route("/predict", methods=["POST"])
def predict():
    start_time = time.perf_counter()
    if model is None:
        REQUEST_COUNT.labels(endpoint="/predict", status="500").inc()
        return jsonify({"error": "Model Production tidak siap"}), 500

    try:
        data = request.get_json()
        if not data or "features" not in data:
            raise ValueError("Payload JSON wajib berisi key 'features'")

        df_input = pd.DataFrame(data["features"])
        preds, probs = run_model_inference(df_input)

        results = []
        for pred, prob in zip(preds, probs):
            results.append({
                "is_anomaly": int(pred),
                "anomaly_probability": round(float(prob), 4),
                "label": "VOLATILITAS TINGGI (ANOMALI)" if int(pred) == 1 else "NORMAL",
            })

        elapsed = time.perf_counter() - start_time
        REQUEST_LATENCY.labels(endpoint="/predict", status="200").observe(elapsed) if False else None
        REQUEST_LATENCY.labels(endpoint="/predict").observe(elapsed)
        REQUEST_COUNT.labels(endpoint="/predict", status="200").inc()

        return jsonify({
            "status": "success",
            "stage": STAGE,
            "model_source": model_source,
            "predictions": results,
        }), 200

    except Exception as e:
        elapsed = time.perf_counter() - start_time
        REQUEST_LATENCY.labels(endpoint="/predict").observe(elapsed)
        REQUEST_COUNT.labels(endpoint="/predict", status="400").inc()
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)