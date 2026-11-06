import os
import sys
import mlflow
from mlflow.tracking import MlflowClient

THRESHOLD_F1 = 0.75
MODEL_NAME = "BitcoinVolatilityDetector"

def get_valid_model_uri(client, run_id):
    """Mencari lokasi model_uri yang valid di MLflow Run."""
    candidate_paths = ["random_forest_model", "model", "random_forest", ""]
    
    # Ambil daftar artifact yang ada di DagsHub run
    try:
        artifacts = client.list_artifacts(run_id)
        artifact_paths = [a.path for a in artifacts]
        print(f"📁 List Artifact di MLflow Run: {artifact_paths}")
        for p in artifact_paths:
            if p not in candidate_paths:
                candidate_paths.insert(0, p)
    except Exception as e:
        print(f"⚠️ Gagal membaca list artifacts: {e}")

    # Cari kandidat path yang memiliki manifest model valid
    for path in candidate_paths:
        uri = f"runs:/{run_id}/{path}".rstrip("/")
        try:
            mlflow.models.get_model_info(uri)
            print(f"🎯 Model URI valid ditemukan: {uri}")
            return uri
        except Exception:
            continue

    # Fallback ke path paling umum di train.py
    return f"runs:/{run_id}/random_forest_model"

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
        
        target_version = None
        # Cek apakah versi model dari run ini sudah terdaftar sebelumnya
        try:
            all_versions = client.search_model_versions(f"name='{MODEL_NAME}'")
            for mv in all_versions:
                if mv.run_id == run_id:
                    target_version = mv.version
                    print(f"ℹ️ Model dari Run ID ini sudah terdaftar sebagai Version {target_version}")
                    break
        except Exception:
            pass

        # Jika belum terdaftar, cari URI artefak dan daftarkan
        if not target_version:
            model_uri = get_valid_model_uri(client, run_id)
            print(f"📦 Mengintegrasikan Model URI ke Registry: {model_uri}")
            registered_model = mlflow.register_model(model_uri=model_uri, name=MODEL_NAME)
            target_version = registered_model.version
        
        # Transisi Stage ke STAGING
        client.transition_model_version_stage(
            name=MODEL_NAME,
            version=target_version,
            stage="Staging",
            archive_existing_versions=False
        )
        print(f"🚀 Model '{MODEL_NAME}' Version {target_version} BERHASIL dipromosikan ke Stage STAGING!")
    else:
        print(f"❌ Model GAGAL memenuhi threshold F1-Score ({f1_score:.4f} < {THRESHOLD_F1}). Registrasi dibatalkan!")
        sys.exit(1)

if __name__ == "__main__":
    main()