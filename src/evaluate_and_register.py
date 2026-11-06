import os
import sys
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
        
        # Urutan kandidat path URI (Root /, random_forest_model, model)
        candidate_uris = [
            f"runs:/{run_id}/",
            f"runs:/{run_id}/random_forest_model",
            f"runs:/{run_id}/model"
        ]
        
        registered_model = None
        used_uri = None

        for uri in candidate_uris:
            try:
                print(f"📦 Mencoba registrasi dari URI: {uri}")
                registered_model = mlflow.register_model(model_uri=uri, name=MODEL_NAME)
                used_uri = uri
                print(f"✅ Berhasil mendaftarkan model dari: {used_uri}")
                break
            except Exception as e:
                print(f"⚠️ Gagal pada URI {uri}: {e}")
                continue

        if not registered_model:
            print("❌ Gagal mendaftarkan model dari seluruh kandidat URI!")
            sys.exit(1)

        version = registered_model.version
        
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