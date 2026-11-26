# LK-10: Model Serving dan Simulasi Scaling Menggunakan MLflow Models & Docker

## 1. Tujuan dan Arsitektur Sistem
Pada tahap LK-10, model **BitcoinVolatilityDetector** tahap `Production` dari MLflow Model Registry dikemas menjadi *Docker Image* inferensi mandiri (`bitcoin-volatility-mlflow-serve:latest`) menggunakan perintah `mlflow models build-docker`. Untuk menjaga ketersediaan layanan dan menangani lonjakan permintaan secara bersamaan (*Horizontal Scaling*), layanan inferensi dijalankan sebanyak **3 replika** di balik *reverse proxy / load balancer* **Nginx**.

### Komponen Layanan dalam Ekosistem
| Layanan / Kontainer | Image | Port Mapping | Peran dalam Arsitektur |
| :--- | :--- | :--- | :--- |
| `mlflow-server` (`mlflow-tracking-server`) | `bitcoin-mlops:latest` | `5000:5000` | MLflow Tracking Server & Model Registry (`Production`) |
| `api-service` (3 Replika: `-1`, `-2`, `-3`) | `bitcoin-volatility-mlflow-serve:latest` | `8081-8083:8080` | 3 instansi REST API inferensi model MLflow (`/ping`, `/invocations`) |
| `nginx-lb` (`bitcoin-volatility-lb`) | `nginx:alpine` | `8000` (Host Mode) | *Load balancer* distribusi trafik *round-robin* ke seluruh replika |

---

## 2. Tahapan Implementasi

### A. Packaging Model dari MLflow Registry ke Docker Image
Model tahap `Production` dibangun menjadi *Docker Image* inferensi berbasis Python/Uvicorn:
```bash
MLFLOW_TRACKING_URI=http://localhost:5000 \
mlflow models build-docker \
  -m "models:/BitcoinVolatilityDetector/Production" \
  -n "bitcoin-volatility-mlflow-serve:latest"
```

### B. Konfigurasi Load Balancer (`nginx.conf`)
Nginx bertindak sebagai pintu masuk tunggal pada port `8000` yang meneruskan permintaan secara *round-robin* ke tiga replika backend (`127.0.0.1:8081`, `127.0.0.1:8082`, dan `127.0.0.1:8083`):
```nginx
upstream mlops_backend {
    server 127.0.0.1:8081;
    server 127.0.0.1:8082;
    server 127.0.0.1:8083;
}

server {
    listen 8000;
    location / {
        proxy_pass http://mlops_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_connect_timeout 10s;
        proxy_read_timeout 60s;
    }
}
```

### C. Orkestrasi Multi-Replika (`docker-compose.yaml`)
Layanan `api-service` dijalankan dengan konfigurasi `deploy.replicas: 3` serta *healthcheck* pada endpoint `/ping` sebelum Nginx menerima lalu lintas eksternal:
```yaml
services:
  mlflow-server:
    image: bitcoin-mlops:latest
    container_name: mlflow-tracking-server
    command: >
      mlflow server
      --backend-store-uri sqlite:////workspaces/MLOps-BitcoinVolatilityDetection/mlflow_store/mlflow.db
      --default-artifact-root /workspaces/MLOps-BitcoinVolatilityDetection/mlruns
      --host 0.0.0.0
      --port 5000
      --workers 1
      --allowed-hosts "*"
      --cors-allowed-origins "*"
    environment:
      - DAGSHUB_REPO_OWNER=lipkusuma
      - DAGSHUB_REPO_NAME=MLOps-BitcoinVolatilityDetection
      - DAGSHUB_TOKEN=${DAGSHUB_TOKEN:-}
    ports:
      - "5000:5000"
    volumes:
      - mlflow-db-data:/workspaces/MLOps-BitcoinVolatilityDetection/mlflow_store
      - mlflow-artifacts-data:/workspaces/MLOps-BitcoinVolatilityDetection/mlruns
    networks:
      - mlops-network
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: unless-stopped

  api-service:
    image: bitcoin-volatility-mlflow-serve:latest
    ports:
      - "8081-8083:8080"
    deploy:
      mode: replicated
      replicas: 3
      restart_policy:
        condition: on-failure
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/ping"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 20s
    depends_on:
      mlflow-server:
        condition: service_healthy
    networks:
      - mlops-network

  nginx-lb:
    image: nginx:alpine
    container_name: bitcoin-volatility-lb
    network_mode: "host"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      api-service:
        condition: service_healthy
    restart: unless-stopped

networks:
  mlops-network:
    driver: bridge

volumes:
  mlflow-db-data:
    driver: local
  mlflow-artifacts-data:
    driver: local
```

---

## 3. Panduan Operasional (Endpoint & Dynamic Scaling)

### A. Menjalankan Ekosistem Layanan
```bash
docker compose up -d
docker compose ps
```

### B. Mengakses Endpoint Inference API (via Nginx Port 8000)
* **Health Check:**
  ```bash
  curl -i http://localhost:8000/ping
  ```
* **Prediksi Volatilitas Bitcoin (`POST /invocations`):**
  ```bash
  curl -X POST http://localhost:8000/invocations \
    -H "Content-Type: application/json" \
    -d '{"dataframe_records": [{"price": 92500.0, "volume": 45000.0, "price_change_pct": 0.085, "volume_change_pct": 1.45}]}'
  ```

### C. Menambah Jumlah Replika Secara Dinamis (*Dynamic Horizontal Scaling*)
Untuk meningkatkan kapasitas layanan secara horizontal (misalnya dari 3 menjadi 5 replika):
1. Perbarui rentang port `api-service` pada `docker-compose.yaml` menjadi `"8081-8085:8080"` dan nilai `replicas: 5`.
2. Tambahkan `server 127.0.0.1:8084;` dan `server 127.0.0.1:8085;` pada blok `upstream mlops_backend` di `nginx.conf`.
3. Terapkan skala baru tanpa menghentikan layanan:
   ```bash
   docker compose up -d --scale api-service=5
   docker compose ps
   ```

---

## 4. Hasil Pengujian Fungsional & Simulasi Beban Tinggi

### A. Verifikasi Endpoint API
* **Health Check (`GET http://localhost:8000/ping`):** Mengembalikan `HTTP/1.1 200 OK`.
* **Prediksi Inferensi (`POST http://localhost:8000/invocations`):** Mengembalikan `HTTP/1.1 200 OK` dengan payload respons `{"predictions": [0]}`.

### B. Hasil Simulasi Beban Paralel (*Stress Test*)
Pengujian dilakukan dengan mengirimkan **30 permintaan prediksi paralel** menggunakan 10 *concurrent worker threads* ke endpoint `http://localhost:8000/invocations`:

| Metrik Pengujian | Hasil Pengukuran |
| :--- | :--- |
| Jumlah Total Permintaan | 30 requests (10 concurrent workers) |
| Total Waktu Penyelesaian | 1.67 detik |
| Throughput | 18.01 Requests/Second (RPS) |
| Latensi Median (p50) | 408.2 ms |
| Latensi Persentil ke-95 (p95) | 1209.1 ms |
| Tingkat Keberhasilan (*Success Rate*) | 100% (`HTTP 200 OK`) |

### C. Analisis Distribusi Beban (*Load Balancing*)
Berdasarkan pemeriksaan log kontainer (`docker compose logs api-service`), permintaan `POST /invocations` terdistribusi merata ke seluruh instansi (`api-service-1`, `api-service-2`, dan `api-service-3`) secara bergantian tanpa mengalami penumpukan antrean maupun *timeout*.