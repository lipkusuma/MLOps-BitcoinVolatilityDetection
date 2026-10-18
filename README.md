# MLOps: Automated Anomaly Detection for Bitcoin Price Volatility

[![Python Version](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Codespaces](https://img.shields.io/badge/GitHub-Codespaces-brightgreen.svg)](https://github.com/codespaces)

## 📌 Deskripsi Proyek
Proyek MLOps ini membangun pipeline otomatisasi untuk mendeteksi dan memprediksi volatilitas harga Bitcoin secara real-time. Sistem ini mencakup otomatisasi ingesti data dari REST API, pembersihan data, data versioning menggunakan DVC, pelacakan eksperimen ML menggunakan MLflow, serta otomatisasi CI/CD menggunakan GitHub Actions.

---

## 👤 Identitas Mahasiswa
- **Nama:** Alif Kusuma Fauzan
- **NIM:** 245150201111051
- **Program Studi:** Teknik Informatika
- **Fakultas:** Ilmu Komputer, Universitas Brawijaya

---

## 🗺️ Peta Jalan Praktikum (Sesuai RPS)

| Modul | Topik Utama RPS | Deskripsi & Fokus Pengerjaan | Status | Dokumen Detail |
| :---: | :--- | :--- | :---: | :--- |
| **LK-01** | Pengantar MLOps | Definisi, urgensi di produksi, perbedaan dengan DevOps, & setup repo | ✅ Selesai | [`docs/LK01_Setup_Environment.md`](./docs/LK01_Setup_Environment.md) |
| **LK-02** | Fondasi DevOps | CI/CD, otomatisasi, dan budaya kolaborasi | ✅ Selesai | [`docs/LK02_Data_Exploration.md`](./docs/LK02_Data_Exploration.md) |
| **LK-03** | Siklus Hidup ML | Konsep pengumpulan data, preprocessing, dan strategi retraining | ✅ Selesai | [`docs/LK03_Preprocessing_Pipeline.md`](./docs/LK03_Preprocessing_Pipeline.md) |
| **LK-04** | Teknik Data Acquisition | Ingestion/scraping REST API CoinGecko via GitHub Actions | ✅ Selesai | [`docs/LK04_Automated_Ingestion.md`](./docs/LK04_Automated_Ingestion.md) |
| **LK-05** | Manajemen Versi | Konsep Data Lineage & integrasi DVC (Tracking v1.0 & v2.0) | ✅ Selesai | [`docs/LK05_DVC_Data_Versioning.md`](./docs/LK05_DVC_Data_Versioning.md) |
| **LK-06** | Eksperimentasi ML | Tracking eksperimen, metrik evaluasi, dan reproduksibilitas | ✅ Selesai | [`docs/LK06_Eksperimentasi_ML.md`](./docs/LK06_Eksperimentasi_ML.md) |
| **LK-07** | Containerization dengan Docker | Kontainerisasi skrip & lingkungan eksekusi pipeline ML | ⏳ Mendatang | `docs/LK07_Containerization_Docker.md` |
| **LK-08** | Pendalaman Konsep CI/CD | Pipeline automation dan integrasi otomatis | ⏳ Mendatang | `docs/LK08_Pipeline_Automation.md` |
| **LK-09** | Orkestrasi Layanan ML | Orkestrasi layanan Machine Learning terintegrasi | ⏳ Mendatang | `docs/LK09_Orkestrasi_Layanan_ML.md` |
| **LK-10** | Serving & Scaling | Serving & scaling sistem Machine Learning di produksi | ⏳ Mendatang | `docs/LK10_Serving_Scaling.md` |
| **LK-11** | Observability | Teknik monitoring performa model & data drift | ⏳ Mendatang | `docs/LK11_Observability_Monitoring.md` |
| **LK-12** | Model Maintenance | Pemeliharaan, kaji ulang, dan pembaruan model berlanjut | ⏳ Mendatang | `docs/LK12_Model_Maintenance.md` |
| **LK-13** | Etika AI dan Tata Kelola | Governance, transparansi, dan etika kecerdasan artifisial | ⏳ Mendatang | `docs/LK13_Etika_AI_Governance.md` |

---

## 📁 Struktur Direktori

Struktur repositori ini mengikuti konvensi standar industri (*Cookiecutter Data Science*) yang disesuaikan dengan kebutuhan MLOps:

```text
MLOps-BitcoinVolatilityDetection/
├── .devcontainer/                 # Konfigurasi otomatisasi GitHub Codespaces
├── .github/
│   └── workflows/
│       └── schedule_ingest.yml    # Workflow GitHub Actions (Automated Ingestion)
├── .dvc/                          # Konfigurasi internal DVC
├── config/                        # File konfigurasi parameter pipeline (yaml)
├── data/                          # Penyimpanan data lokal & pointer DVC
│   ├── raw/                       # Data mentah hasil ingestion & pointer .dvc
│   └── processed/                 # Data terproses siap latih & pointer .dvc
├── docs/                          # Laporan & dokumentasi detail per Lembar Kerja
│   ├── LK01_Setup_Environment.md
│   ├── LK02_Data_Exploration.md
│   ├── LK03_Preprocessing_Pipeline.md
│   ├── LK04_Automated_Ingestion.md
│   ├── LK05_DVC_Data_Versioning.md
│   └── LK06_Eksperimentasi_ML.md  # Dokumentasi eksperimen MLflow & Model Metadata
├── mlruns/                        # MLflow local tracking store directory
├── models/                        # Artefak model terpercaya / terlatih
├── notebooks/                     # Jupyter Notebooks untuk EDA & eksperimen awal
├── src/                           # Source code modular produksi
│   ├── ingest_data.py             # Skrip penarikan data dinamis (CoinGecko REST API)
│   ├── preprocess.py              # Skrip prapemrosesan & feature engineering
│   ├── train.py                   # Skrip pelatihan model terintegrasi MLflow Tracking API
│   └── utils/                     # Fungsi pembantu & utility
├── .gitignore                     # Pengabaian file lokal oleh Git
├── LICENSE                        # Lisensi proyek (MIT)
├── README.md                      # Dokumentasi utama proyek
└── requirements.txt               # Daftar dependensi library Python
```

---

## 🛠️ Perkakas & Teknologi

| Komponen | Teknologi | Fungsi Utama |
| :--- | :--- | :--- |
| **Language** | Python 3.10 | Bahasa pemrograman utama |
| **Data Ingestion** | CoinGecko API, `requests` | Penarikan data harga & volatilitas Bitcoin |
| **Data Processing** | Pandas, PyArrow | Pembersihan data & format Parquet |
| **Data Versioning** | DVC (Data Version Control) | Melacak versi dataset tanpa beban di Git |
| **Experiment Tracking** | MLflow Tracking API | Pelacakan parameter, metrik, artefak, & model |
| **Machine Learning** | Scikit-Learn | Algoritma Random Forest Classifier |
| **CI/CD Automation** | GitHub Actions | Penarikan data otomatis & pembuatan Artifacts |