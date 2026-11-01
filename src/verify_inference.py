import pandas as pd
import mlflow.pyfunc

MODEL_NAME = "BitcoinVolatilityDetector"
STAGE = "Production"

print(f"📌 Memuat model dari MLflow Registry [models:/{MODEL_NAME}/{STAGE}]...")

model_uri = f"models:/{MODEL_NAME}/{STAGE}"
loaded_model = mlflow.pyfunc.load_model(model_uri)
print("✅ Model Production (Version 3) berhasil dimuat!")

sample_data = pd.DataFrame([
    {
        "price": 65000.0,
        "volume": 1200.5,
        "price_change_pct": 0.005,
        "volume_change_pct": 0.02
    },
    {
        "price": 58000.0,
        "volume": 9800.0,
        "price_change_pct": -0.092,
        "volume_change_pct": 1.85
    }
])

predictions = loaded_model.predict(sample_data)
sample_data["predicted_anomaly"] = predictions
sample_data["label"] = sample_data["predicted_anomaly"].map({0: "NORMAL", 1: "VOLATILITAS TINGGI (ANOMALI)"})

print("\n=== HASIL VERIFIKASI INFERENSI MODEL PRODUCTION ===")
for i, row in sample_data.iterrows():
    print(f"Sampel #{i+1}: Price={row['price']}, PriceChg={row['price_change_pct']}, VolChg={row['volume_change_pct']}")
    print(f" -> Prediksi: {row['predicted_anomaly']} ({row['label']})\n")