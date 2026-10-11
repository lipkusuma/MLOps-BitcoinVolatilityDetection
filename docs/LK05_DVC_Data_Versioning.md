# 🚀 Panduan Manajemen Versi Data & Continual Learning DVC (LK-05)

Berikut adalah langkah-langkah detail untuk mengintegrasikan DVC (Data Version Control), melacak dataset versi `v1.0` & `v2.0`, dan menguji *lineage* data via `dvc diff`.

---

### Langkah 1: Inisialisasi DVC & Local Remote Storage
Jalankan perintah berikut untuk menginisialisasi DVC dan menyiapkan tempat penyimpanan *cache* biner data di luar Git:

```bash
# Inisialisasi DVC di repositori
dvc init

# Membuat direktori remote storage lokal
mkdir -p ../dvc_remote_storage

# Mengonfigurasi remote storage DVC
dvc remote add -d local_remote ../dvc_remote_storage

# Commit konfigurasi awal DVC ke Git
git commit -m "build: initialize dvc and setup local remote storage"
```

---

### Langkah 2: Tracking Dataset Baseline Versi 1.0 (`v1.0`)
Jalankan perintah DVC untuk melacak file dataset mentah dan olahan versi awal:

```bash
# Tambahkan dataset ke pelacakan DVC
dvc add data/raw/btc_raw_latest.csv data/processed/btc_cleaned.parquet

# Push biner data ke remote storage
dvc push

# Commit file pointer .dvc ke Git dan beri Tag v1.0
git add data/raw/btc_raw_latest.csv.dvc data/processed/btc_cleaned.parquet.dvc data/raw/.gitignore data/processed/.gitignore
git commit -m "feat: track dataset v1.0 using dvc"
git tag -a "v1.0" -m "Dataset Version 1.0 - Initial Baseline Data"
```

---

### Langkah 3: Simulasi Continual Learning & Versioning Versi 2.0 (`v2.0`)
Simulasikan penambahan *batch* data baru dengan mengeksekusi ulang pipeline *ingestion* & *preprocessing*, lalu perbarui versi DVC:

```bash
# Ingest data batch baru & lakukan preprocessing
python src/ingest_data.py
python src/preprocess.py

# Perbarui tracking DVC dengan data terbaru
dvc add data/raw/btc_raw_latest.csv data/processed/btc_cleaned.parquet
dvc push

# Commit pointer .dvc baru ke Git dan beri Tag v2.0
git commit -m "feat: update dataset to v2.0 with new ingestion batch"
git tag -a "v2.0" -m "Dataset Version 2.0 - Updated Batch Data"
```

---

### Langkah 4: Audit Silsilah Data (`dvc status` & `dvc diff`)
Jalankan perintah berikut untuk mengaudit transisi perubahan data antara versi `v1.0` dan `v2.0`:

```bash
# Memastikan status data lokal sinkron dengan remote
dvc status

# Melihat statistik perubahan data antar-tag
dvc diff v1.0 v2.0
```

- **Verifikasi Hasil Audit:**
  Output terminal akan menampilkan `2 modified` (`btc_cleaned.parquet` & `btc_raw_latest.csv`), membuktikan bahwa DVC berhasil mencatat perubahan *hash* MD5 data tanpa membebani repositori Git.