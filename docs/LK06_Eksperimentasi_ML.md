# 🚀 Panduan Manajemen Eksperimen & Pelacakan Metrik MLflow (LK-06)

Dokumen ini memuat laporan teknis integrasi MLflow Tracking, pelacakan *hyperparameter*, metrik evaluasi, artefak visual, serta dokumentasi metadata model pada proyek **Bitcoin Volatility Detection**.

---

## 📌 1. Deskripsi Eksperimen & Strategi Pemodelan
- **Tugas Pemodelan:** Klasifikasi Biner (*Binary Classification*) untuk memprediksi kejadian anomali volatilitas harga Bitcoin.
- **Sumber Dataset:** Data terversi dari DVC (`data/processed/btc_cleaned.parquet`).
- **Algoritma:** Random Forest Classifier (`sklearn.ensemble.RandomForestClassifier`).
- **Sistem Tracking:** MLflow Tracking API (`mlflow.log_param`, `mlflow.log_metric`, `mlflow.log_artifact`, `mlflow.sklearn.log_model`).
- **Prioritas Metrik Kuantitatif:** **F1-Score** dan **Recall**. Dalam konteks risiko finansial, meminimalkan *False Negative* (anomali harga tidak terdeteksi) adalah kunci utama.
- **Eliminasi Data Leakage:** Kolom pembentuk target biner (`z_score`, `rolling_volatility_14`, `rolling_volatility_24h`, `timestamp`, `datetime`) dieksklusi dari himpunan fitur $X$. Fitur terpakai: `price`, `volume`, `price_change_pct`, `volume_change_pct`.

---

## 🛠️ 2. Langkah Implementasi Kode (`src/train.py`)

Skrip dirancang modular dengan penerimaan argumen CLI (`argparse`) untuk memfasilitasi eksperimentasi multi-run.

```bash
# Perintah Eksekusi 4 Runs Utama:

# Run 1: Baseline Model (Underfitting Test)
python src/train.py --n_estimators 50 --max_depth 3 --run_name "rf_baseline_v1"

# Run 2: Moderate Depth Tuning (Improving)
python src/train.py --n_estimators 100 --max_depth 6 --run_name "rf_tuned_depth_v2"

# Run 3: Deep Forest Optimal (Best Model)
python src/train.py --n_estimators 200 --max_depth 10 --run_name "rf_optimal_v3"

# Run 4: Deep Overfitting Test (Saturasi)
python src/train.py --n_estimators 300 --max_depth 20 --run_name "rf_deep_overfit_v4"
```

### Ringkasan Fungsi Logging MLflow dalam Kode:
1. `mlflow.set_tags()`: Mengunci metadata penulis (Alif Kusuma Fauzan / 245150201111051), versi dataset (`v2.0_DVC`), dan jenis tugas.
2. `mlflow.log_params()`: Mencatat `n_estimators`, `max_depth`, `min_samples_split`, `random_state`, serta dimensi sampel data.
3. `mlflow.log_metrics()`: Mencatat `accuracy`, `precision`, `recall`, `f1_score`, dan `roc_auc`.
4. `mlflow.log_artifact()`: Menyimpan gambar visualisasi `confusion_matrix.png` langsung ke storage run MLflow.
5. `mlflow.sklearn.log_model()`: Menyimpan biner model Scikit-Learn beserta contoh input data schema (`input_example`).

---

## 📊 3. Hasil Tabel Perbandingan Eksperimen MLflow

Berikut adalah rekapitulasi data dari 4 *runs* utama yang dieksekusi:

| Run Name | `n_estimators` | `max_depth` | `min_samples_split` | Accuracy ↑ | Precision ↑ | Recall ↑ | F1-Score ↑ | ROC-AUC ↑ | Evaluasi Performa |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `rf_baseline_v1` | 50 | 3 | 5 | 0.9718 | 0.0000 | 0.0000 | 0.0000 | 0.9085 | 🔴 **Underfitting** |
| `rf_tuned_depth_v2` | 100 | 6 | 5 | 0.9859 | 1.0000 | 0.5000 | 0.6667 | 0.8324 | 🟡 **Improving** |
| **`rf_optimal_v3`** | **200** | **10** | **5** | **0.9930** | **1.0000** | **0.7500** | **0.8571** | **0.8415** | 🟢 **BEST MODEL** |
| `rf_deep_overfit_v4` | 300 | 20 | 5 | 0.9930 | 1.0000 | 0.7500 | 0.8571 | 0.8397 | ⚪ **Saturasi / Overfit** |

---

## 🧠 4. Analisis Hyperparameter & Perilaku Model

1. **Underfitting (`rf_baseline_v1` - `max_depth=3`):**
   - Pohon keputusan terlalu dangkal sehingga gagal mengenali pola anomali.
   - Terjadi *Paradox Akurasi*: Akurasi terlihat sangat tinggi (97.18%) dikarenakan ketidakseimbangan kelas (sebagian besar data bernilai Normal), tetapi Precision, Recall, dan F1-Score bernilai **0.0000** karena tidak ada 1 pun sampel anomali yang berhasil terdeteksi.

2. **Model Optimal (`rf_optimal_v3` - `max_depth=10`, `n_estimators=200`):**
   - Merupakan kombinasi terbaik yang menghasilkan **F1-Score tertinggi (0.8571)** dan **Recall 0.7500**.
   - Precision mencapai 100% (1.0000), meminimalkan risiko *False Positive* pada deteksi anomali.

3. **Saturasi Performa (`rf_deep_overfit_v4` - `max_depth=20`, `n_estimators=300`):**
   - Menambah kedalaman pohon melebihi 10 tidak memberikan peningkatan F1-Score maupun Recall, mengindikasikan bahwa kapasitas model telah mengalami saturasi.

---

## 📋 5. Detail Metadata Model Terbaik untuk Deployment (Challenger Model)

Model **`rf_optimal_v3`** dipilih secara resmi untuk dipromosikan ke tahap deployment berikutnya (LK-07 / Service Inference):

```yaml
Model Metadata:
  Model Family: Random Forest Classifier
  MLflow Run Name: rf_optimal_v3
  MLflow Run ID: 1acf96d32dd44553b216fe4301504f94
  Experiment Name: Bitcoin_Volatility_Detection
  
Hyperparameters:
  n_estimators: 200
  max_depth: 10
  min_samples_split: 5
  random_state: 42

Metrics (Test Set N=142):
  accuracy: 0.9929577
  precision: 1.0000000
  recall: 0.7500000
  f1_score: 0.8571428
  roc_auc: 0.8414855

Artifacts:
  Model Artifact Path: mlruns/1/1acf96d32dd44553b216fe4301504f94/artifacts/model
  Confusion Matrix Plot: confusion_matrix.png

Tags Metadata:
  author: Alif Kusuma Fauzan
  nim: "245150201111051"
  model_family: Random Forest
  dataset_version: v2.0_DVC
  task: Binary Classification
```

---

## 🔬 6. Analisis Confusion Matrix (`rf_optimal_v3`)

Dari total 142 data sampel pengujian (test set):
- **True Normal (TN):** 138 data berhasil diprediksi sebagai kondisi normal dengan tepat.
- **False Positive (FP):** 0 data (tidak ada alarm palsu).
- **False Negative (FN):** 1 data anomali yang terlewat.
- **True Anomaly (TP):** 3 data anomali berhasil dideteksi dengan sempurna.

---

## 🛠️ 7. Perintah Eksekusi & Akses MLflow UI

1. **Jalankan Ulang Seluruh Pelatihan Model (4 Runs):**
   ```bash
   python src/train.py --n_estimators 50 --max_depth 3 --run_name "rf_baseline_v1"
   python src/train.py --n_estimators 100 --max_depth 6 --run_name "rf_tuned_depth_v2"
   python src/train.py --n_estimators 200 --max_depth 10 --run_name "rf_optimal_v3"
   python src/train.py --n_estimators 300 --max_depth 20 --run_name "rf_deep_overfit_v4"
   ```

2. **Jalankan Server MLflow UI:**
   ```bash
   mlflow ui --host 0.0.0.0 --port 5000
   ```
3. Akses dashboard visual di browser melalui URL `http://localhost:5000`.