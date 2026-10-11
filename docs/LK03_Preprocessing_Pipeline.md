# 🚀 Panduan Preprocessing Pipeline & Rekayasa Fitur (LK-03)

Berikut adalah langkah-langkah detail untuk pembersihan data mentah Bitcoin, pembentukan fitur indikator volatilitas, dan ekspor dataset Parquet.

---

### Langkah 1: Persiapan Environment Preprocessing
Pastikan pustaka `pyarrow` terpasang untuk mendukung pemrosesan format Apache Parquet:

```bash
pip install pyarrow numpy pandas
```

---

### Langkah 2: Eksekusi Prapemrosesan Data & Feature Engineering
Jalankan skrip preprocessing untuk mengolah data mentah menjadi dataset siap latih:

```bash
python src/preprocess.py
```

- **Mekanisme Kerja Skrip:**
  1. Membaca file data mentah dari `data/raw/btc_raw_latest.csv`.
  2. Membersihkan nilai hilang (*missing values*) dan baris duplikat, lalu mengurutkan data berdasarkan waktu secara kronologis.
  3. **Rekayasa Fitur Volatilitas:**
     - `log_return`: Menghitung persentase perubahan logaritma harga antar-periode ($\ln(P_t / P_{t-1})$).
     - `volatility_24h`: Menghitung *rolling standard deviation* dari *log return* dengan jendela waktu 24 jam.
  4. **Labeling Anomali Volatilitas:** Membentuk variabel target biner `is_high_volatility` (1 jika volatilitas melebihi ambang batas 2 standar deviasi, 0 jika normal).
  5. Mengekspor dataset bersih ke format Parquet di `data/processed/btc_cleaned.parquet`.

---

### Langkah 3: Verifikasi Dataset Parquet Siap Latih
Jalankan perintah berikut di terminal untuk memeriksa statistik fitur hasil prapemrosesan:

```bash
python -c "import pandas as pd; df=pd.read_parquet('data/processed/btc_cleaned.parquet'); print(df.describe())"
```