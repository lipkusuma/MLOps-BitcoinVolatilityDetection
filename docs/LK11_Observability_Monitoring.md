# LK-11: Implementasi Observability dan Dashboard Monitoring Model ML

## 1. Ringkasan & Tujuan
Praktikum **LK-11** membangun sistem pemantauan operasional dan kualitas prediksi secara proaktif untuk layanan inferensi **BitcoinVolatilityDetector** yang telah di-*deploy* secara multi-replika pada LK-10. Sistem ini mengintegrasikan **Prometheus** (*time-series metrics collector*) dan **Grafana** (*real-time visualization dashboard*) ke dalam orkestrasi `docker-compose.yaml` guna mendeteksi potensi *Silent Failure*, *Data Drift*, *Prediction Drift*, dan *Model Decay* secara dini.

### Tujuan Kegiatan
1. Menambahkan layanan `prometheus` dan `grafana` ke dalam `docker-compose.yaml` (lanjutan dari LK-09 dan LK-10) dengan manajemen penyimpanan ringan di GitHub Codespaces.
2. Mengekspos endpoint `/metrics` pada ketiga kontainer API model menggunakan pustaka `prometheus-client`.
3. Mengonfigurasi *scraper* Prometheus melalui `prometheus.yml` untuk menarik metrik dari seluruh replika model setiap 5 detik.
4. Merancang dashboard visual di Grafana (8 panel) yang memantau metrik operasional (latensi `p50`/`p95`, *throughput*, *error rate*, CPU/RAM) sekaligus metrik kualitas model (*Prediction Drift* dan *Data Drift*).
5. Menjalankan simulasi beban kerja 3 replika serta injeksi pergeseran distribusi data (*Data Drift*) untuk memverifikasi respons dashboard secara *real-time*.

---

## 2. Arsitektur Observability Sistem

```text
                        ┌───────────────────────────────────────┐
  Client / Simulator ──►│   Nginx Load Balancer (Port 8000)     │
                        └───────────────────┬───────────────────┘
                                            │ Round-Robin
                   ┌────────────────────────┼────────────────────────┐
                   ▼                        ▼                        ▼
      ┌────────────────────────┐ ┌────────────────────────┐ ┌────────────────────────┐
      │   api-service-1        │ │   api-service-2        │ │   api-service-3        │
      │   127.0.0.1:8081       │ │   127.0.0.1:8082       │ │   127.0.0.1:8083       │
      │   (/invocations,       │ │   (/invocations,       │ │   (/invocations,       │
      │    /predict, /metrics) │ │    /predict, /metrics) │ │    /predict, /metrics) │
      └───────────┬────────────┘ └───────────┬────────────┘ └───────────┬────────────┘
                  │                          │                          │
                  └──────────────────────────┼──────────────────────────┘
                                             │ Scrape /metrics (interval: 5s)
                                             ▼
                                ┌─────────────────────────┐
                                │   Prometheus Server     │
                                │   127.0.0.1:9090        │
                                │   (TSDB Retention: 2d)  │
                                └────────────┬────────────┘
                                             │ PromQL Query (refresh: 5s)
                                             ▼
                                ┌─────────────────────────┐
                                │   Grafana Dashboard     │
                                │   127.0.0.1:3000        │
                                │   (8 Monitoring Panels) │
                                └─────────────────────────┘
```

### Komponen Utama
- **Instrumented Inference API (`app.py` & `Dockerfile`):** Dibangun di atas layer `bitcoin-mlops:latest` (`bitcoin-mlops-monitored:latest`) dengan pustaka `prometheus-client` untuk mengekspos endpoint `/metrics` pada ketiga replika (`8081`, `8082`, `8083`).
- **Prometheus Scraper (`prometheus.yml`):** Menarik metrik operasional dan ML dari target `bitcoin-volatility-api` (`127.0.0.1:8081-8083`) dan `prometheus` (`127.0.0.1:9090`) setiap **5 detik** dengan retensi TSDB 2 hari (`--storage.tsdb.retention.time=2d`).
- **Grafana Visualization (`grafana/provisioning/datasources/prometheus.yml`):** Terhubung otomatis ke Prometheus (`http://127.0.0.1:9090`) dan menampilkan 8 panel pemantauan aktif dengan *auto-refresh* setiap **5 detik**.

---

## 3. Konfigurasi Prometheus (`prometheus.yml`)

```yaml
global:
  scrape_interval: 5s
  evaluation_interval: 5s

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["127.0.0.1:9090"]

  - job_name: "bitcoin-volatility-api"
    metrics_path: "/metrics"
    static_configs:
      - targets:
          - "127.0.0.1:8081"
          - "127.0.0.1:8082"
          - "127.0.0.1:8083"
        labels:
          service: "api-service"
          environment: "production"
```

---

## 4. Panduan Menjalankan Stack Monitoring

1. **Jalankan seluruh layanan MLOps & Observability:**
   ```bash
   docker compose up -d --build
   docker compose ps
   ```
2. **Verifikasi Target Scraping pada Prometheus:**
   - Buka `http://localhost:9090/targets` melalui browser.
   - Pastikan seluruh endpoint pada *job* `bitcoin-volatility-api` (`127.0.0.1:8081`, `8082`, `8083`) dan `prometheus` (`127.0.0.1:9090`) berstatus **`UP`**.
3. **Akses & Pantau Dashboard Grafana:**
   - Buka `http://localhost:3000` (kredensial: `admin` / `admin`).
   - Buka dashboard **MLOps Observability - Bitcoin Volatility Detection (LK-11)** dan atur rentang waktu ke `Last 5 minutes` dengan interval refresh `5s`.
4. **Kirim Simulasi Trafik & Data Drift:**
   - Kirim permintaan prediksi `POST` ke `http://localhost:8000/invocations` dengan payload `dataframe_records` (`price`, `volume`, `price_change_pct`, `volume_change_pct`) untuk mengamati distribusi beban di ketiga replika dan respons detektor *drift*.

---

## 5. Makna Metrik & Justifikasi Threshold Alert

| Pilar / Kategori | Nama Metrik Prometheus | Makna & Fungsi Pemantauan | Threshold Alert | Justifikasi Penetapan Threshold |
| :--- | :--- | :--- | :--- | :--- |
| **Operasional — Throughput** | `mlops_inference_requests_total` | Mengukur jumlah *request* per detik (`rate`) yang ditangani masing-masing replika (`8081`–`8083`). | `< 0.01 req/s` pada jam operasional | Mendeteksi terputusnya aliran trafik dari Nginx atau gangguan pada layanan hulu. |
| **Operasional — Latensi** | `mlops_inference_latency_seconds` | Mengukur distribusi waktu proses inferensi persentil ke-50 (`p50`) dan ke-95 (`p95`). | `p95 > 1000 ms` selama > 2 menit | Menjaga SLA respons *real-time* agar tidak terjadi penumpukan antrean pada 3 replika API. |
| **Operasional — Reliabilitas** | `mlops_inference_requests_total{status!="200"}` | Persentase kegagalan inferensi (*HTTP Error Rate*). | `> 5%` selama > 2 menit | Menghindari *alert fatigue* akibat kesalahan sesaat namun segera memperingatkan jika terjadi kegagalan skema input atau model. |
| **Operasional — Resource** | `process_cpu_seconds_total` & `process_resident_memory_bytes` | Memantau pemanfaatan CPU (%) dan konsumsi RAM (MB) setiap instansi kontainer API. | `CPU > 80%` atau `RAM > 512 MB` | Menjadi sinyal kebutuhan penambahan replika (*horizontal scaling* `--scale api-service=N`) sebelum terjadi *Out-of-Memory* (OOM). |
| **Performa ML — Prediction Drift** | `mlops_predictions_total` & `mlops_anomaly_score` | Memantau proporsi kelas keluaran (`0_normal` vs `1_anomaly`) serta distribusi skor probabilitas anomali. | Rasio kelas anomali `> 40%` atau `0%` berkepanjangan | Pergeseran distribusi output $P(\hat{Y})$ secara mendadak mengindikasikan model mulai bias atau kehilangan sensitivitas terhadap rezim pasar baru. |
| **Performa ML — Data Drift** | `mlops_feature_drift_zscore` & `mlops_feature_rolling_mean` | Mengukur simpangan rata-rata berjalan (*rolling mean* 50 sampel terakhir) fitur input (`price`, `volume`, `price_change_pct`, `volume_change_pct`) terhadap *baseline* data latih. | **Warning:** `Z-Score > 1.5`<br>**Critical:** `Z-Score > 2.0` | Simpangan lebih dari 2 standar deviasi ($|Z| > 2.0$) menunjukkan distribusi input $P(X)$ telah bergeser signifikan keluar dari distribusi pelatihan model. |

---

## 6. Hasil Verifikasi & Simulasi Beban Kerja

- **Status Target Prometheus (`http://localhost:9090/targets`):** Keempat target aktif dengan status **`UP`** (`bitcoin-volatility-api` **3/3 up** pada port `8081`, `8082`, `8083` dan `prometheus` **1/1 up** pada port `9090`) dengan durasi *scraping* **2–4 ms**.
- **Distribusi Beban 3 Replika & Reliabilitas:** Saat simulasi beban dijalankan melalui Nginx (`port 8000`), ketiga replika mencatat distribusi trafik dan utilisasi sumber daya seimbang (RAM stabil di kisaran **260–262 MB** per kontainer, CPU **0.5%–2.5%**, latensi `p50` ~150 ms, `p95` ~250–480 ms, dan **HTTP Error Rate 0%**).
- **Deteksi Data Drift Real-Time:** Injeksi skenario anomali harga dan volume Bitcoin ekstrem menyebabkan metrik `mlops_feature_drift_zscore` pada panel *Data Drift Detector* melonjak ke rentang **2.7–4.3** (melampaui batas kritis `2.0`).

---

## 7. Analisis Monitoring: Deteksi Penurunan Performa Model (*Model Decay*)

Dalam sistem Machine Learning produksi, model dapat mengalami ***Silent Failure***—kondisi ketika infrastruktur berstatus *uptime* 100% tanpa error HTTP, namun kualitas prediksinya menurun karena pola dunia nyata berubah (*Model Decay*). Selain itu, label kebenaran (*ground truth*) pergerakan pasar kripto tidak selalu langsung tersedia seketika (*ground truth delay*).

Dashboard Grafana LK-11 mendeteksi *Model Decay* secara proaktif melalui tiga mekanisme utama:
1. **Deteksi Dini Data Drift ($P(X)$) melalui Feature Z-Score Shift:** Ketika karakteristik data input yang masuk (seperti lonjakan harga atau volume perdagangan Bitcoin ekstrem) menyimpang dari statistik *baseline* pelatihan, grafik **Data Drift Detector** segera menandai kenaikan `mlops_feature_drift_zscore` melewati ambang batas **`2.0`**, sementara grafik **Rolling Mean** menunjukkan fitur spesifik yang bergeser.
2. **Deteksi Prediction Drift ($P(\hat{Y})$) melalui Distribusi Prediksi:** Pergeseran distribusi fitur input yang memengaruhi perilaku keputusan model terpantau langsung pada panel **Distribusi Prediksi Model**, sehingga anomali rasio kelas prediksi (`0_normal` vs `1_anomaly`) dapat dikenali sebelum kerugian bisnis terjadi.
3. **Isolasi Akar Masalah (Infrastruktur vs Kualitas Model):** Dengan menyandingkan metrik kesehatan sistem (*Latensi p50/p95*, *Error Rate 0%*, *CPU/RAM*) dengan metrik *drift* dalam satu dashboard, tim MLOps dapat memastikan bahwa penurunan kualitas prediksi bukan disebabkan oleh keterbatasan komputasi, melainkan kebutuhan untuk memicu proses pelatihan ulang model (*Continuous Training* pada LK-12).