# 🚀 Panduan Otomatisasi Ingesti Data via GitHub Actions (LK-04)

Berikut adalah langkah-langkah detail untuk mengeksekusi pipeline pengumpulan dan prapemrosesan data secara berurutan di terminal serta mengonfigurasi otomatisasi CI/CD.

---

### Langkah 1: Persiapan Environment
Pastikan seluruh dependensi library Python sudah terpasang:

```bash
pip install -r requirements.txt
```

---

### Langkah 2: Eksekusi Penarikan Data (Data Ingestion)
Jalankan skrip untuk mengambil data real-time harga dan volume Bitcoin dari CoinGecko API:

```bash
python src/ingest_data.py
```

- **Mekanisme Kerja Skrip:**
  1. Mengirim permintaan HTTP GET ke REST API CoinGecko dengan *exception handling* lengkap untuk menangani `HTTPError`, `ConnectionError`, dan `Timeout`.
  2. Menyimpan data mentah baru ke `data/raw/btc_raw_YYYYMMDD_HHMMSS.csv` sebagai arsip non-destruktif.
  3. Memperbarui pointer data mentah paling mutakhir di `data/raw/btc_raw_latest.csv`.

---

### Langkah 3: Eksekusi Prapemrosesan Data (Preprocessing)
Jalankan skrip untuk membersihkan data mentah dan membentuk fitur-fitur indikator volatilitas:

```bash
python src/preprocess.py
```

- **Mekanisme Kerja Skrip:**
  1. Membaca data mentah dari `data/raw/btc_raw_latest.csv`.
  2. Membersihkan baris duplikat dan mengisi nilai hilang menggunakan teknik *forward-fill* (`ffill`).
  3. Menghitung fitur persentase perubahan harga/volume, *rolling volatility*, dan nilai statistik *z-score*.
  4. Membentuk label target biner `is_anomaly` (1 = Anomali Volatilitas Ekstrem, 0 = Kondisi Normal).
  5. Mengekspor dataset bersih ke format biner berkinerja tinggi `data/processed/btc_cleaned.parquet`.

---

### Langkah 4: Otomatisasi Pipeline via GitHub Actions (Artifacts Mode)
Workflow dikonfigurasi pada `.github/workflows/schedule_ingest.yml` untuk mengeksekusi penarikan data secara berkala dan menyimpannya sebagai **Artifacts** (tanpa mengotori *history commit* Git).

- **Verifikasi Artifacts di GitHub:**
  1. Buka tab **Actions** di repositori GitHub.
  2. Pilih eksekusi *workflow* **Scheduled Data Ingestion**.
  3. Unduh file zip dataset pada seksi **Artifacts** di bagian bawah halaman.