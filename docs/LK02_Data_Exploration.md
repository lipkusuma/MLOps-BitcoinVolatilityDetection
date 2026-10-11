# 🚀 Panduan Eksplorasi Data & API Ingestion (LK-02)

Berikut adalah langkah-langkah detail untuk mengeksekusi eksplorasi REST API CoinGecko dan menjalankan skrip penarikan data historis Bitcoin.

---

### Langkah 1: Persiapan Endpoint API & Dependencies
Pastikan pustaka `requests` dan `pandas` sudah terpasang pada environment:

```bash
pip install requests pandas
```

---

### Langkah 2: Eksekusi Penarikan Data (Data Ingestion)
Jalankan skrip untuk mengambil data harga dan volume Bitcoin secara dinamis melalui REST API CoinGecko:

```bash
python src/ingest_data.py
```

- **Mekanisme Kerja Skrip:**
  1. Mengirim permintaan HTTP GET ke endpoint API CoinGecko (`/coins/bitcoin/market_chart`) untuk mengambil data *time-series* harga (BTC/USD) dan volume perdagangan.
  2. Menerapkan *exception handling* (`try-except`) untuk menangani potensi eror jaringan, *timeout*, atau batasan kuota (*rate limiting*).
  3. Mengonversi data JSON dari API menjadi DataFrame Pandas dengan format waktu standar `datetime`.
  4. Menyimpan data mentah ke `data/raw/btc_raw_latest.csv`.

---

### Langkah 3: Verifikasi Output Data Mentah
Jalankan perintah berikut untuk mengecek isi file data mentah hasil *ingestion*:

```bash
python -c "import pandas as pd; print(pd.read_csv('data/raw/btc_raw_latest.csv').head())"
```

- **Struktur Output Data Mentah:**
  - `timestamp`: Stempel waktu Unix dalam milidetik.
  - `price`: Harga Bitcoin dalam satuan USD.
  - `volume`: Total volume transaksi dalam 24 jam.
  - `datetime`: Stempel waktu terformat YYYY-MM-DD HH:MM:SS.