# 🚀 Panduan Model Registry, Versioning, Transisi Stage & Kontainerisasi Docker (LK-07)

Dokumen ini memuat laporan teknis pendaftaran model ke MLflow Model Registry, pengelolaan 4 versi model (v1 s.d. v4), transisi stage (Staging -> Production), sinkronisasi metadata DVC, pembuatan REST API server (`app.py`), serta pengujian kontainer Docker.

---

## 📌 1. Deskripsi Model Registry & Strategi Lifecycle

| Parameter | Konfigurasi / Detail |
| :--- | :--- |
| **Model Registered Name** | `BitcoinVolatilityDetector` |
| **Version 1 (None)** | `rf_baseline_v1` (Run ID: `88537df6399c491186f763a0ae81a91f`). Baseline model mengalami *Underfitting*. |
| **Version 2 (None)** | `rf_tuned_depth_v2` (Run ID: `39ca3ed42ee44e569d518fec2b00feaa`). Performa mengalami peningkatan (*Improving*). |
| **Version 3 (Production)** | `rf_optimal_v3` (Run ID: `1acf96d32dd44553b216fe4301504f94`). **BEST MODEL**, F1-Score 0.8571 dan Precision 1.0000 tanpa *overfitting*. |
| **Version 4 (Staging)** | `rf_deep_overfit_v4` (Run ID: `24d496f25a4c42d2b3c20e43e1d70884`). Diposisikan di Staging sebagai model pembanding berkapasitas tinggi. |
| **Metadata Lineage DVC** | Dilacak via `models/active_model.yaml.dvc`. |
| **Serving Mechanism** | Layanan REST API memuat model secara dinamis dari Registry menggunakan URI `models:/BitcoinVolatilityDetector/Production`. |

---

## 📊 2. Perbandingan Versi Model & Evaluasi Lifecycle

| Model Version | Run Name | Stage | F1-Score | Precision | Recall | Accuracy | Status Evaluasi & Alasan Penetapan Stage |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Version 1** | `rf_baseline_v1` | **None** | 0.0000 | 0.0000 | 0.0000 | 0.9436 | Model baseline mengalami *Underfitting* (kedalaman pohon terlalu dangkal). |
| **Version 2** | `rf_tuned_depth_v2` | **None** | 0.6667 | 1.0000 | 0.5000 | 0.9788 | Performa membaik namun *Recall* belum optimal. |
| **Version 3** | `rf_optimal_v3` | **Production** | **0.8571** | **1.0000** | **0.7500** | **0.9930** | **BEST MODEL**, F1-Score tertinggi, bebas dari risiko *overfitting*. |
| **Version 4** | `rf_deep_overfit_v4` | **Staging** | 0.8571 | 1.0000 | 0.7500 | 0.9930 | Parameter `max_depth=20` mengalami saturasi & berisiko *overfit*. |

---

## 🧠 3. Analisis Transisi Stage & Sinkronisasi DVC

- **Manajemen Governan Model:** Pemisahan status `Staging` dan `Production` menjamin bahwa layanan inferensi publik hanya mengakses versi model yang terverifikasi aman dan berkinerja terbaik (**Version 3**).
- **Data Lineage dengan DVC:** Metadata file `models/active_model.yaml` mengikat skema fitur, hyperparameter, dan metrik Version 3 langsung ke komit DVC dataset `v2.0_DVC` (`data/processed/btc_cleaned.parquet`).

---

## 📋 4. Detail Metadata Serving Model Produksi

```yaml
model_registry:
  name: BitcoinVolatilityDetector
  active_version: 3
  stage: Production
  run_id: 1acf96d32dd44553b216fe4301504f94
  model_family: Random Forest Classifier
  hyperparameters:
    n_estimators: 200
    max_depth: 10
    min_samples_split: 5
    random_state: 42
  metrics:
    f1_score: 0.8571428571428571
    precision: 1.0
    recall: 0.75
    accuracy: 0.9929577464788732
  feature_contract:
    - price
    - volume
    - price_change_pct
    - volume_change_pct
  data_lineage:
    dataset_version: v2.0_DVC
    dataset_path: data/processed/btc_cleaned.parquet
```

---

## 🔬 5. Verifikasi Inferensi & Output Responses

### A. Output Verification Script (`python src/verify_inference.py`)

```text
📌 Memuat model dari MLflow Registry:
   [models:/BitcoinVolatilityDetector/Production]...
✅ Model Production (Version 3) berhasil dimuat!

=== HASIL VERIFIKASI INFERENSI MODEL PRODUCTION ===
Sampel #1:
  Price = 65000.0, PriceChg = 0.005, VolChg = 0.02
  -> Prediksi: 0 (NORMAL)

Sampel #2:
  Price = 58000.0, PriceChg = -0.092, VolChg = 1.85
  -> Prediksi: 1 (VOLATILITAS TINGGI (ANOMALI))
```

### B. Response Prediction Endpoint (`POST /predict`)

```json
{
  "predictions": [
    {
      "is_anomaly": 0,
      "label": "NORMAL"
    },
    {
      "is_anomaly": 1,
      "label": "VOLATILITAS TINGGI (ANOMALI)"
    }
  ],
  "stage": "Production",
  "status": "success"
}
```

---

## 🛠️ 6. Perintah Eksekusi Build, Run & Testing Docker

1. **Jalankan Registrasi 4 Versi & Transisi Stage:**
   ```bash
   python src/register_and_transition.py
   ```

2. **Jalankan Verifikasi Inferensi:**
   ```bash
   python src/verify_inference.py
   ```

3. **Build Docker Image:**
   ```bash
   docker build -t bitcoin-volatility-api:v1 .
   ```

4. **Jalankan Kontainer Docker:**
   ```bash
   docker run -d -p 5000:5000 --name btc-volatility-service bitcoin-volatility-api:v1
   ```

5. **Uji Endpoint Prediction:**
   ```bash
   curl -X POST http://localhost:5000/predict \
     -H "Content-Type: application/json" \
     -d '{
       "features": [
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
       ]
     }'
   ```