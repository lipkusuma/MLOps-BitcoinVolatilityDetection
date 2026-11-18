import os
import json
import pandas as pd
import skops.io as sio
import mlflow
import mlflow.pyfunc
import mlflow.sklearn
from mlflow.tracking import MlflowClient
from flask import Flask, request, jsonify

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
    "https://dagshub.com/lipkusuma/MLOps-BitcoinVolatilityDetection.mlflow"
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

# 1. Utama: Muat dari kontainer mlflow-server via Docker Bridge Network (Service Discovery)
try:
    model_uri = f"models:/{MODEL_NAME}/{STAGE}"
    model = mlflow.pyfunc.load_model(model_uri)
    model_source = f"Docker MLflow Server ({model_uri})"
    print(f"✅ Model dimuat dari MLflow Server kontainer: {model_uri}", flush=True)
except Exception as e:
    print(f"⚠️ Model belum terdaftar di MLflow Server, melakukan registrasi otomatis: {e}", flush=True)
    if TRACKING_URI and os.path.exists(FALLBACK_RUN_PATH):
        try:
            sk_model = mlflow.sklearn.load_model(FALLBACK_RUN_PATH)
            mlflow.set_experiment("Bitcoin-Volatility-Orchestration")
            with mlflow.start_run(run_name="docker-compose-registry-seed"):
                mlflow.sklearn.log_model(
                    sk_model=sk_model,
                    artifact_path="model",
                    registered_model_name=MODEL_NAME
                )
            client = MlflowClient(tracking_uri=TRACKING_URI)
            latest_versions = client.get_latest_versions(MODEL_NAME)
            if latest_versions:
                ver = latest_versions[-1].version
                client.transition_model_version_stage(
                    name=MODEL_NAME,
                    version=ver,
                    stage=STAGE,
                    archive_existing_versions=True
                )
            model_uri = f"models:/{MODEL_NAME}/{STAGE}"
            model = mlflow.pyfunc.load_model(model_uri)
            model_source = f"Docker MLflow Server ({model_uri})"
            print(f"✅ Model berhasil didaftarkan & dimuat dari MLflow Server: {model_uri}", flush=True)
        except Exception as seed_err:
            print(f"⚠️ Auto-seed MLflow Server gagal: {seed_err}", flush=True)

# 2. Fallback Cloud Remote: Muat dari DagsHub Model Registry
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

# 3. Fallback Lokal: Artifact Path MLruns
if model is None:
    try:
        if os.path.exists(FALLBACK_RUN_PATH):
            model = mlflow.pyfunc.load_model(FALLBACK_RUN_PATH)
            model_source = f"Local MLruns Artifact ({FALLBACK_RUN_PATH})"
            print(f"✅ Model dimuat dari Fallback Artifact Path: {FALLBACK_RUN_PATH}", flush=True)
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

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({
        "status": "online",
        "system": "Bitcoin Volatility & Anomaly Detection API",
        "tracking_uri": mlflow.get_tracking_uri(),
        "dagshub_remote": DAGSHUB_MLFLOW_URI,
        "model_registry": MODEL_NAME,
        "active_stage": STAGE,
        "model_source": model_source,
        "author": metadata.get("tags", {}).get("author", "Alif Kusuma Fauzan"),
        "nim": metadata.get("tags", {}).get("nim", "245150201111051"),
        "model_loaded": model is not None
    }), 200

@app.route("/predict", methods=["POST"])
def predict():
    if model is None:
        return jsonify({"error": "Model Production tidak siap"}), 500

    try:
        data = request.get_json()
        if not data or "features" not in data:
            return jsonify({"error": "Payload JSON wajib berisi key 'features'"}), 400

        expected_features = ["price", "volume", "price_change_pct", "volume_change_pct"]
        df_input = pd.DataFrame(data["features"])

        missing_cols = [col for col in expected_features if col not in df_input.columns]
        if missing_cols:
            return jsonify({"error": f"Fitur berikut kurang: {missing_cols}"}), 400

        df_input = df_input[expected_features]
        preds = model.predict(df_input).tolist()

        results = []
        for pred in preds:
            results.append({
                "is_anomaly": int(pred),
                "label": "VOLATILITAS TINGGI (ANOMALI)" if pred == 1 else "NORMAL"
            })

        return jsonify({
            "status": "success",
            "stage": STAGE,
            "model_source": model_source,
            "predictions": results
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)