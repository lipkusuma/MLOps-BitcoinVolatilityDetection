import mlflow
from mlflow.tracking import MlflowClient

client = MlflowClient()
MODEL_NAME = "BitcoinVolatilityDetector"

# 4 Run ID dari eksperimen LK-06
RUNS = [
    {
        "run_id": "88537df6399c491186f763a0ae81a91f",
        "name": "rf_baseline_v1",
        "desc": "Version 1 (rf_baseline_v1). Hyperparameter: n_estimators=50, max_depth=3. Metrik: F1=0.0000. Underfitting."
    },
    {
        "run_id": "39ca3ed42ee44e569d518fec2b00feaa",
        "name": "rf_tuned_depth_v2",
        "desc": "Version 2 (rf_tuned_depth_v2). Hyperparameter: n_estimators=100, max_depth=6. Metrik: F1=0.6667, Recall=0.5000. Improving."
    },
    {
        "run_id": "1acf96d32dd44553b216fe4301504f94",
        "name": "rf_optimal_v3",
        "desc": "Version 3 (rf_optimal_v3). Hyperparameter: n_estimators=200, max_depth=10. Metrik: F1=0.8571, Recall=0.7500, Precision=1.0000. BEST MODEL untuk Production."
    },
    {
        "run_id": "24d496f25a4c42d2b3c20e43e1d70884",
        "name": "rf_deep_overfit_v4",
        "desc": "Version 4 (rf_deep_overfit_v4). Hyperparameter: n_estimators=300, max_depth=20. Metrik: F1=0.8571. Overfit/Saturasi risk."
    }
]

print("📌 1. Mendaftarkan 4 Versi Model ke MLflow Model Registry...")

for run_info in RUNS:
    model_uri = f"runs:/{run_info['run_id']}/model"
    mv = mlflow.register_model(model_uri, MODEL_NAME)
    client.update_model_version(
        name=MODEL_NAME,
        version=mv.version,
        description=run_info["desc"]
    )
    print(f"✅ Registered {run_info['name']} -> Model Registry Version {mv.version}")

client.update_registered_model(
    name=MODEL_NAME,
    description="Sistem Deteksi Anomali Volatilitas Harga Bitcoin (BTC/USD) berbasis MLflow Model Registry."
)

print("\n📌 2. Melakukan Transisi Stage...")

# Version 4 (rf_deep_overfit_v4) -> Staging
client.transition_model_version_stage(
    name=MODEL_NAME,
    version="4",
    stage="Staging",
    archive_existing_versions=False
)
print("🔄 Version 4 (rf_deep_overfit_v4) dipindahkan ke Stage: Staging")

# Version 3 (rf_optimal_v3) -> Production
client.transition_model_version_stage(
    name=MODEL_NAME,
    version="3",
    stage="Production",
    archive_existing_versions=True
)
print("🚀 Version 3 (rf_optimal_v3) resmi dipromosikan ke Stage: Production!")