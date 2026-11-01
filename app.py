import os
import json
import pandas as pd
import skops.io as sio
import mlflow
import mlflow.pyfunc
from flask import Flask, request, jsonify

app = Flask(__name__)

MODEL_NAME = os.getenv("MODEL_NAME", "BitcoinVolatilityDetector")
STAGE = os.getenv("STAGE", "Production")
METADATA_PATH = os.getenv("METADATA_PATH", "models/metadata/model_metadata.json")
MODEL_SKOPS_PATH = os.getenv("MODEL_PATH", "models/model.skops")
FALLBACK_RUN_PATH = "mlruns/1/models/m-9099abb51028425ebef7f3f4634748d8/artifacts"

if os.path.exists("mlflow.db"):
    mlflow.set_tracking_uri("sqlite:///mlflow.db")

metadata = {}
model = None

if os.path.exists(METADATA_PATH):
    with open(METADATA_PATH, "r") as f:
        metadata = json.load(f)

# 1. Coba muat dari MLflow Model Registry
try:
    model_uri = f"models:/{MODEL_NAME}/{STAGE}"
    model = mlflow.pyfunc.load_model(model_uri)
    print(f"✅ Model Production dimuat dari MLflow Registry: {model_uri}")
except Exception as e:
    print(f"⚠️ Registry load error: {e}")

# 2. Fallback: Coba muat langsung dari MLflow Artifact Path jika Registry uri belum resolve
if model is None:
    try:
        if os.path.exists(FALLBACK_RUN_PATH):
            model = mlflow.pyfunc.load_model(FALLBACK_RUN_PATH)
            print(f"✅ Model Production dimuat dari Fallback Artifact Path: {FALLBACK_RUN_PATH}")
    except Exception as e:
        print(f"⚠️ Artifact path load error: {e}")

# 3. Fallback Biner Skops
if model is None:
    try:
        if os.path.exists(MODEL_SKOPS_PATH):
            skops_m = sio.load(MODEL_SKOPS_PATH, trusted=True)
            class SkopsWrapper:
                def __init__(self, m):
                    self.m = m
                def predict(self, df):
                    return self.m.predict(df)
            model = SkopsWrapper(skops_m)
            print(f"✅ Model dimuat dari file Skops lokal: {MODEL_SKOPS_PATH}")
    except Exception as e:
        print(f"❌ Skops load error: {e}")

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({
        "status": "online",
        "system": "Bitcoin Volatility & Anomaly Detection API",
        "model_registry": MODEL_NAME,
        "active_stage": STAGE,
        "active_version": "3",
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
            "predictions": results
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)