# MLOps: Automated Anomaly Detection for Bitcoin Price Volatility

[![Python Version](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Codespaces](https://img.shields.io/badge/GitHub-Codespaces-brightgreen.svg)](https://github.com/codespaces)

## 📌 Deskripsi Proyek
Proyek MLOps ini membangun pipeline terotomasi untuk mendeteksi anomali volatilitas ekstrem pada harga Bitcoin secara real-time menggunakan CoinGecko API. Sistem ini dilengkapi dengan kemampuan **Continual Learning (CT)** berbasis pemicu *Data Drift* (Evidently AI) untuk mencegah *model degradation* di pasar kripto yang dinamis.

---

## 🗂️ Struktur Direktori
Struktur repositori ini mengikuti konvensi standar industri (*Cookiecutter Data Science*):

```text
├── .devcontainer/       # Konfigurasi otomatisasi GitHub Codespaces
├── config/              # File konfigurasi parameter pipeline (yaml)
├── data/                # Penyimpanan data lokal
│   ├── raw/             # Data mentah hasil ingestion (CSV archive & latest)
│   └── processed/       # Data terproses siap latih (Parquet format)
├── models/              # Artefak model terpercaya / terlatih
├── notebooks/           # Jupyter Notebooks untuk EDA & eksperimen awal
├── src/                 # Source code modular produksi
│   ├── ingest_data.py   # Skrip penarikan data dinamis (CoinGecko REST API)
│   ├── preprocess.py    # Skrip prapemrosesan & feature engineering
│   └── utils/           # Fungsi pembantu & utility
├── requirements.txt     # Daftar dependensi library Python
├── LICENSE              # Lisensi proyek (MIT)
└── README.md            # Dokumentasi utama proyek
```

---

## 🚀 Panduan Eksekusi Pipeline Data (LK-04)

Berikut adalah langkah-langkah detail untuk mengeksekusi pipeline pengumpulan dan prapemrosesan data secara berurutan di terminal GitHub Codespaces:

### Langkah 1: Persiapan Environment
Pastikan seluruh dependensi library Python sudah terpasang:
```bash
pip install -r requirements.txt
```

### Langkah 2: Eksekusi Penarikan Data (Data Ingestion)
Jalankan skrip untuk mengambil data real-time harga dan volume Bitcoin 24 jam terakhir dari CoinGecko API:
```bash
python src/ingest_data.py
```
* **Mekanisme Kerja Skrip:**
  1. Mengirim permintaan HTTP GET ke REST API CoinGecko dengan *exception handling* lengkap untuk menangani `HTTPError`, `ConnectionError`, dan `Timeout`.
  2. Menyimpan data mentah baru ke `data/raw/btc_raw_YYYYMMDD_HHMMSS.csv` sebagai arsip non-destruktif.
  3. Memperbarui pointer data mentah paling mutakhir di `data/raw/btc_raw_latest.csv`.

### Langkah 3: Eksekusi Prapemrosesan Data (Preprocessing)
Jalankan skrip untuk membersihkan data mentah dan membentuk fitur-fitur indikator volatilitas:
```bash
python src/preprocess.py
```
* **Mekanisme Kerja Skrip:**
  1. Membaca data mentah dari `data/raw/btc_raw_latest.csv`.
  2. Membersihkan baris duplikat dan mengisi nilai hilang menggunakan teknik *forward-fill* (`ffill`).
  3. Menghitung fitur persentase perubahan harga/volume, `rolling_volatility_14` (jendela 70 menit), dan nilai statistik `z_score`.
  4. Membentuk label target biner `is_anomaly` (1 = Anomali Volatilitas Ekstrem, 0 = Kondisi Normal).
  5. Mengekspor dataset bersih ke format biner berkinerja tinggi `data/processed/btc_cleaned.parquet`.

### Langkah 4: Verifikasi Output Data
Untuk memastikan dataset Parquet berhasil dibuat dan siap digunakan pada tahap pemodelan MLflow:
```bash
python -c "import pandas as pd; print(pd.read_parquet('data/processed/btc_cleaned.parquet').head())"
```