# LK-09: Orkestrasi Layanan ML Terintegrasi Menggunakan Docker Compose

**Mata Kuliah:** Machine Learning Operations (MLOps) — Teknik Informatika Kelas B  
**Nama:** Alif Kusuma Fauzan (245150201111051)  
**Dosen Pengampu:** Rizal Setya Perdana, S.Kom., M.Kom., Ph.D.  
**Link Repositori:** https://github.com/lipkusuma/MLOps-BitcoinVolatilityDetection  
**DagsHub Remote:** https://dagshub.com/lipkusuma/MLOps-BitcoinVolatilityDetection  

---

## 1. Pendahuluan & Tujuan

Pada tahap pengembangan dan produksi sistem Machine Learning, menjalankan layanan secara terpisah menggunakan perintah `docker run` manual menimbulkan risiko ketidakkonsistenan urutan *startup*, perubahan alamat IP dinamis antar-kontainer, serta hilangnya metadata dan artefak model ketika kontainer dihentikan.

Praktikum **LK-09** mentransformasikan layanan inferensi model deteksi anomali volatilitas Bitcoin menjadi ekosistem multi-layanan yang terorkestrasi secara deklaratif melalui satu berkas **`docker-compose.yaml`**, dengan tetap mempertahankan integrasi ke **DagsHub Cloud Remote** dari tahapan LK-05 hingga LK-08.

### Tujuan Kegiatan LK-09
1. Mengorkestrasi minimal dua layanan ML yang saling terintegrasi (`mlflow-server` dan `api-service`) menggunakan `docker-compose.yaml`.
2. Menerapkan komunikasi antar-kontainer berbasis nama layanan (*Service Discovery*) melalui *custom bridge network* (`mlops-network`).
3. Menjamin persistensi metadata eksperimen/registry dan artefak model menggunakan Docker *named volumes* (`mlflow-db-data` dan `mlflow-artifacts-data`).
4. Mengatur urutan *startup* layanan menggunakan `depends_on` dengan kondisi `service_healthy` agar API inferensi baru berjalan setelah server tracking MLflow siap sepenuhnya.
5. Memverifikasi ketahanan sistem melalui uji skenario gangguan (`docker compose down` diikuti `docker compose up -d`).

---

## 2. Arsitektur Ekosistem & Anatomi `docker-compose.yaml`

Sistem orkestrasi dirancang menggunakan pola *shared container image* (`bitcoin-mlops:latest`) untuk mengoptimalkan penggunaan ruang penyimpanan (*disk resource*), dengan pembagian peran layanan sebagai berikut:

| Komponen / Nama | Tipe | Peran & Konfigurasi Utama |
|---|---|---|
| `mlflow-server` (`mlflow-tracking-server`) | Service | Menjalankan MLflow Tracking & Model Registry pada port `5000` (`--workers 1`, `--allowed-hosts "*"`), menyimpan metadata SQLite di `/mlflow_store` dan artefak model di `/mlruns`. |
| `api-service` (`bitcoin-volatility-api`) | Service | Layanan REST API Flask pada port `8000:5000` yang terhubung ke `http://mlflow-server:5000` untuk memuat model `models:/BitcoinVolatilityDetector/Production` serta memiliki *fallback* ke DagsHub Cloud Registry. |
| `mlops-network` | Custom Bridge Network | Jaringan terisolasi dengan DNS internal otomatis sehingga kontainer berkomunikasi menggunakan nama layanan (`mlflow-server`), bukan alamat IP statis. |
| `mlflow-db-data` | Named Volume | Menyimpan berkas database SQLite (`mlflow.db`) secara permanen di luar siklus hidup kontainer. |
| `mlflow-artifacts-data` | Named Volume | Menyimpan seluruh artefak model dan eksperimen (`mlruns/`) yang dibagi antara `mlflow-server` dan `api-service`. |
| `depends_on` (`service_healthy`) | Dependency & Healthcheck | Memastikan `api-service` menunggu hingga endpoint `/health` pada `mlflow-server` mengembalikan status `200 OK` sebelum proses inisialisasi model dimulai. |

---

## 3. Implementasi Service Discovery & Integrasi Hybrid DagsHub

1. **Service Discovery Antar-Kontainer:**  
   Pada variabel lingkungan `api-service`, `MLFLOW_TRACKING_URI` diatur ke `http://mlflow-server:5000`. Docker Compose secara otomatis memetakan nama layanan `mlflow-server` ke alamat IP internal kontainer aktif di dalam jaringan `mlops-network`.
2. **Keamanan & Aksesibilitas Middleware MLflow:**  
   Flag `--allowed-hosts "*"` dan `--cors-allowed-origins "*"` dikonfigurasi pada `mlflow server` agar permintaan HTTP internal yang membawa header `Host: mlflow-server:5000` diterima dengan aman oleh *security middleware* MLflow.
3. **Integrasi Hybrid dengan DagsHub Cloud Remote:**  
   Selain memuat model utama dari kontainer lokal `mlflow-server` (`models:/BitcoinVolatilityDetector/Production`), `api-service` juga dikonfigurasi dengan `DAGSHUB_MLFLOW_URI` (`https://dagshub.com/lipkusuma/MLOps-BitcoinVolatilityDetection.mlflow`) sebagai *cloud registry fallback* sehingga tetap selaras dengan pipeline CI/CD GitHub Actions (LK-08).

---

## 4. Hasil Eksekusi & Verifikasi Sistem

### A. Status Kontainer Terorkestrasi (`docker compose ps`)
Eksekusi `docker compose up -d --build` menghasilkan kedua layanan berjalan bersamaan dalam satu jaringan terisolasi:
- `mlflow-tracking-server`: Status `Up (healthy)` pada `0.0.0.0:5000->5000/tcp`.
- `bitcoin-volatility-api`: Status `Up` pada `0.0.0.0:8000->5000/tcp`.

### B. Pengujian Komunikasi Antar-Kontainer & Inferensi (`GET /` dan `POST /predict`)
Pengujian pada `http://localhost:8000/` mengonfirmasi bahwa `api-service` berhasil menarik model langsung dari kontainer `mlflow-server`:

```json
{
    "active_stage": "Production",
    "author": "Alif Kusuma Fauzan",
    "dagshub_remote": "[https://dagshub.com/lipkusuma/MLOps-BitcoinVolatilityDetection.mlflow](https://dagshub.com/lipkusuma/MLOps-BitcoinVolatilityDetection.mlflow)",
    "model_loaded": true,
    "model_registry": "BitcoinVolatilityDetector",
    "model_source": "Docker MLflow Server (models:/BitcoinVolatilityDetector/Production)",
    "nim": "245150201111051",
    "status": "online",
    "system": "Bitcoin Volatility & Anomaly Detection API",
    "tracking_uri": "http://mlflow-server:5000"
}
```

Pengujian inferensi pada `POST /predict` dengan data pasar Bitcoin (`price: 92500.0`, `volume: 45000.0`, `price_change_pct: 0.085`, `volume_change_pct: 1.45`) mengembalikan prediksi anomali secara sukses (`200 OK`) menggunakan model yang dimuat dari `Docker MLflow Server`.

### C. Uji Skenario Gangguan & Persistensi Volume
Saat dilakukan simulasi gangguan dengan mematikan dan menghapus seluruh kontainer menggunakan perintah `docker compose down`, kedua *named volumes* (`mlops-bitcoinvolatilitydetection_mlflow-db-data` dan `mlops-bitcoinvolatilitydetection_mlflow-artifacts-data`) tetap bertahan. Ketika layanan dijalankan ulang dengan `docker compose up -d`, `api-service` langsung memuat model terdaftar dari `mlflow-server` tanpa kehilangan metadata maupun artefak model.

---

## 5. Urutan Perintah Eksekusi Terminal

```bash
# 1. Build image bersama dan jalankan seluruh layanan di background
docker compose up -d --build

# 2. Verifikasi status kesehatan kontainer
docker compose ps

# 3. Verifikasi komunikasi API <-> MLflow Server & pengujian prediksi
curl -s http://localhost:8000/ | python -m json.tool
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [{"price": 92500.0, "volume": 45000.0, "price_change_pct": 0.085, "volume_change_pct": 1.45}]}' | python -m json.tool

# 4. Uji skenario gangguan & verifikasi persistensi volume
docker compose down
docker compose up -d
docker volume ls | grep mlflow
```

---

## 6. Kesimpulan

1. Orkestrasi multi-layanan menggunakan `docker-compose.yaml` berhasil menyatukan `mlflow-server` dan `api-service` dalam satu perintah deklaratif (`docker compose up -d`), mempermudah replikasi lingkungan di mesin lain.
2. Konfigurasi *custom bridge network* (`mlops-network`) dan `depends_on` (`service_healthy`) menjamin *Service Discovery* yang andal serta urutan *startup* bebas *race condition*.
3. Pemanfaatan Docker *named volumes* terbukti menjaga persistensi database metadata dan artefak model secara penuh meskipun seluruh kontainer dimatikan dan dibangun ulang.