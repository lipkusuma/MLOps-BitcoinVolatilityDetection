# LK-08: Otomatisasi End-to-End Pipeline (Integrasi "Code as a Trigger")

---

## 1. Pendahuluan & Tujuan

Praktikum LK-08 bertujuan untuk menerapkan prinsip utama MLOps: **"Code as a Trigger"**. Pada tahap ini, alur kerja diotomatiskan menggunakan **GitHub Actions** yang terintegrasi penuh dengan **DagsHub Cloud Remote** (DVC dan MLflow Tracking/Registry). 

Setiap terjadi perubahan pada kode (misalnya modifikasi hyperparameter atau skrip pemrosesan data), pipeline CI/CD akan terpicu secara otomatis untuk melakukan pengujian unit (*testing*), pelatihan ulang model (*retraining*), evaluasi performa berbasis ambang batas (*threshold*), hingga pendaftaran model ke registry berstatus **Staging** tanpa intervensi manual.

---

## 2. Solusi Ephemeral Runner & Arsitektur DagsHub Cloud

Runner GitHub Actions bersifat sementara (*ephemeral*), di mana file lokal (seperti SQLite `mlflow.db` dan penyimpanan DVC lokal) akan terhapus begitu job selesai. Untuk menjamin reproduksibilitas dan keterlacakan artefak secara permanen, sistem dihubungkan ke **DagsHub**:

1. **DVC Cloud Remote (DagsHub Storage):** Dataset terversi `btc_cleaned.parquet` ditarik secara otomatis dari remote DagsHub (`https://dagshub.com/lipkusuma/MLOps-BitcoinVolatilityDetection.dvc`) di awal eksekusi pipeline runner (`dvc pull -r origin`).
2. **MLflow Tracking & Registry Cloud (DagsHub Server):** Server MLflow terpusat diatur ke URI `https://dagshub.com/lipkusuma/MLOps-BitcoinVolatilityDetection.mlflow` menggunakan autentikasi terenkripsi via GitHub Secret `DAGSHUB_TOKEN`.

---

## 3. Tahapan Alur Kerja Otomatisasi Pipeline

Pipeline terdiri dari 4 tahapan berantai yang terdefinisi di `.github/workflows/mlops-automation.yaml`:

`[Git Push / PR] ──► [Tahap 1: Pytest] ──► [Tahap 2: Retraining] ──► [Tahap 3 & 4: Eval & Auto-Staging]`

### A. Tahap 1: Automated Testing (`tests/test_pipeline.py`)
Memverifikasi integritas sistem sebelum pelatihan dilakukan:
- **`test_dataset_exists`**: Memastikan file dataset terversi DVC tersedia.
- **`test_feature_columns_and_no_leakage`**: Memastikan ketersediaan 4 fitur input (`price`, `volume`, `price_change_pct`, `volume_change_pct`) dan ketiadaan fitur penyebab *Data Leakage* (`z_score`, `rolling_volatility_14`).
- **`test_target_binary`**: Memastikan label target bersifat biner ($0$ atau $1$).

### B. Tahap 2: Automated Training (`src/train.py`)
Menjalankan skrip pelatihan model Random Forest secara terisolasi di cloud runner, kemudian mencatat metrik evaluasi dan parameter secara otomatis ke server DagsHub MLflow.

### C. Tahap 3 & 4: Model Evaluation & Auto-Staging (`src/evaluate_and_register.py`)
- Membaca metrik $F1$-score dari run pelatihan terbaru di DagsHub MLflow.
- Membandingkan $F1$-score terhadap ambang batas kelulusan **$F1 \ge 0.75$**.
- Jika lolos validasi, model didaftarkan ke MLflow Model Registry `BitcoinVolatilityDetector` dan dipromosikan ke stage **`Staging`**. Jika gagal, pendaftaran dibatalkan dan pipeline dinyatakan gagal (*Build Fail*).

---

## 4. Berkas dan Komponen Utama

| Nama Berkas | Tipe / Lokasi | Fungsi Teknis |
|---|---|---|
| `.github/workflows/mlops-automation.yaml` | Workflows CI/CD | Spesifikasi pemicu push/PR, instruksi `dvc pull`, `pytest`, `train.py`, dan evaluasi auto-staging. |
| `tests/test_pipeline.py` | Unit Test Script | Verifikasi integritas data masukan dan proteksi terhadap Data Leakage. |
| `src/evaluate_and_register.py` | Evaluation & Registry Script | Evaluasi threshold performa $F1 \ge 0.75$ dan otomatisasi transisi stage model ke `Staging`. |
| `docs/LK08_Pipeline_Automation.md` | Dokumentasi Teknis | Penjelasan detail arsitektur CI/CD dan pencegahan *silent failures*. |

---

## 5. Pengujian & Verifikasi Pipeline

### A. Pengujian Unit Test Lokal (Pytest)
Untuk memastikan seluruh logika pengujian dan integritas dataset valid di lingkungan lokal sebelum dikirim ke remote:
```bash
pytest tests/ -v
```

### B. Verifikasi Evaluasi & Auto-Staging Script (Manual Run Check)
Eksekusi langsung skrip evaluasi dengan mengarahkan variabel lingkungan ke server DagsHub:
```bash
export MLFLOW_TRACKING_URI="[https://dagshub.com/lipkusuma/MLOps-BitcoinVolatilityDetection.mlflow](https://dagshub.com/lipkusuma/MLOps-BitcoinVolatilityDetection.mlflow)"
export MLFLOW_TRACKING_USERNAME="lipkusuma"
export MLFLOW_TRACKING_PASSWORD="<DAGSHUB_TOKEN>"

python src/evaluate_and_register.py
```

### C. Pemeriksaan Status Model Registry via MLflow Client Python
Gunakan skrip singkat berikut untuk mengonfirmasi versi model teraktif di stage `Staging`:
```python
import os
import mlflow
from mlflow.tracking import MlflowClient

mlflow.set_tracking_uri("[https://dagshub.com/lipkusuma/MLOps-BitcoinVolatilityDetection.mlflow](https://dagshub.com/lipkusuma/MLOps-BitcoinVolatilityDetection.mlflow)")
client = MlflowClient()

staging_versions = client.get_latest_versions("BitcoinVolatilityDetector", stages=["Staging"])
for version in staging_versions:
    print(f"Model: {version.name} | Version: {version.version} | Stage: {version.current_stage} | Run ID: {version.run_id}")
```