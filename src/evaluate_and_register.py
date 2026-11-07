import os
import sys

# Kunci timeout request HTTP maksimal 30 detik agar tidak pernah hanging di DagsHub
os.environ["MLFLOW_HTTP_REQUEST_TIMEOUT"] = "30"

import mlflow
from mlflow.tracking import MlflowClient

THRESHOLD_F1 = 0.75
MODEL_NAME = "BitcoinVolatilityDetector"

def main():
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        print("❌ MLFLOW_TRACKING_URI belum diatur!")
        sys.exit(1)
        
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient()

    experiment = mlflow.get_experiment_by_name("Bitcoin_Volatility_Detection")
    if not experiment:
        print("❌ Eksperimen 'Bitcoin_Volatility_Detection' tidak ditemukan di MLflow!")
        sys.exit(1)

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["attribute.start_time DESC"],
        max_results=1
    )
    if not runs:
        print("❌ Tidak ada run pelatihan yang ditemukan!")
        sys.exit(1)

    latest_run = runs[0]
    run_id = latest_run.info.run_id
    f1_score = latest_run.data.metrics.get("f1_score", 0.0)

    print(f"📊 MLflow Run ID Terbaru : {run_id}")
    print(f"🎯 Metrik F1-Score       : {f1_score:.4f} (Threshold minimal: {THRESHOLD_F1})")

    if f1_score >= THRESHOLD_F1:
        print(f"✅ Model LOLOS evaluasi threshold (F1 >= {THRESHOLD_F1})!")
        
        # Buat Registered Model container jika belum ada
        try:
            client.create_registered_model(MODEL_NAME)
            print(f"✨ Registered Model '{MODEL_NAME}' berhasil disiapkan.")
        except Exception:
            print(f"ℹ️ Registered Model '{MODEL_NAME}' sudah tersedia.")

        # Daftarkan versi model langsung via REST API Client (instan tanpa download/inspect)
        model_source = f"runs:/{run_id}/random_forest_model"
        try:
            mv = client.create_model_version(
                name=MODEL_NAME,
                source=model_source,
                run_id=run_id,
                description=f"Auto-staged by GitHub Actions CI/CD (F1={f1_score:.4f})"
            )
            version = mv.version
        except Exception as e:
            print(f"⚠️ Registrasi path fallback: {e}")
            mv = client.create_model_version(
                name=MODEL_NAME,
                source=f"runs:/{run_id}/model",
                run_id=run_id,
                description=f"Auto-staged by GitHub Actions CI/CD (F1={f1_score:.4f})"
            )
            version = mv.version

        print(f"📦 Version {version} berhasil terdaftar di DagsHub Model Registry.")

        # Transisi Stage ke STAGING
        client.transition_model_version_stage(
            name=MODEL_NAME,
            version=version,
            stage="Staging",
            archive_existing_versions=False
        )
        print(f"🚀 Model '{MODEL_NAME}' Version {version} BERHASIL dipromosikan ke Stage STAGING!")
    else:
        print(f"❌ Model GAGAL memenuhi threshold F1-Score ({f1_score:.4f} < {THRESHOLD_F1}). Registrasi dibatalkan!")
        sys.exit(1)

if __name__ == "__main__":
    main()