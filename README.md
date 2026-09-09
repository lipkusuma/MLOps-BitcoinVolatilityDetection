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
│   ├── raw/             # Data mentah hasil ingestion dari API
│   └── processed/       # Data terproses & tervalidasi siap latih
├── models/              # Artefak model terpercaya / terlatih
├── notebooks/           # Jupyter Notebooks untuk EDA & eksperimen awal
├── src/                 # Source code modular produksi
│   ├── ingestion/       # Skrip penarikan data (CoinGecko Worker)
│   ├── models/          # Skrip pelatihan & evaluasi ML
│   └── utils/           # Fungsi pembantu & penguji kuesioner data
├── requirements.txt     # Daftar dependensi library Python
├── LICENSE              # Lisensi proyek (MIT)
└── README.md            # Dokumentasi utama proyek