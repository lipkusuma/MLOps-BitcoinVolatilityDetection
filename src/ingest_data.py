"""
Module untuk penarikan data dinamis Bitcoin (Harga & Volume) dari CoinGecko REST API.
Mendukung penyimpanan non-destruktif dan penanganan error koneksi.
"""

import os
import sys
from datetime import datetime
import requests
import pandas as pd


def fetch_bitcoin_data() -> pd.DataFrame | None:
    """
    Menarik data pergerakan harga dan volume Bitcoin 7 hari terakhir dari CoinGecko API
    untuk memastikan volume data mencukupi (>= 500 baris).
    
    Returns:
        pd.DataFrame | None: DataFrame data mentah atau None jika terjadi kegagalan API.
    """
    # Mengubah days=1 menjadi days=7 agar data yang didapat > 500 baris
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=30"
    headers = {"User-Agent": "Mozilla/5.0"}

    print("🔄 Mengirim permintaan HTTP GET ke CoinGecko REST API...")

    # 1. Error Handling & Timeout Management
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"❌ HTTP Error terjadi: {http_err} (Status Code: {response.status_code})")
        return None
    except requests.exceptions.ConnectionError:
        print("❌ Error Koneksi: Gagal terhubung ke server CoinGecko. Periksa jaringan Anda.")
        return None
    except requests.exceptions.Timeout:
        print("❌ Timeout Error: Permintaan ke API melebihi batas waktu (15 detik).")
        return None
    except requests.exceptions.RequestException as err:
        print(f"❌ Critical Error: {err}")
        return None

    # 2. Parsing Response JSON
    prices = data.get("prices", [])
    volumes = data.get("total_volumes", [])

    if not prices or not volumes:
        print("❌ Data Kosong: Respons API tidak memiliki atribut 'prices' atau 'total_volumes'.")
        return None

    df_price = pd.DataFrame(prices, columns=["timestamp", "price"])
    df_vol = pd.DataFrame(volumes, columns=["timestamp", "volume"])
    df = pd.merge(df_price, df_vol, on="timestamp")

    # Konversi timestamp milidetik ke Datetime UTC
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

    # 3. Penyimpanan Non-Destruktif
    os.makedirs("data/raw", exist_ok=True)
    
    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    archive_path = f"data/raw/btc_raw_{timestamp_str}.csv"
    latest_path = "data/raw/btc_raw_latest.csv"

    # Simpan sebagai arsip berkala dan perbarui pointer latest
    df.to_csv(archive_path, index=False)
    df.to_csv(latest_path, index=False)

    # 4. Tampilan Logging Terminal Interaktif
    df_display = df.copy()
    df_display["utc"] = df_display["timestamp"].dt.strftime("%H:%M UTC")
    df_display["wib"] = df_display["timestamp"].dt.tz_localize("UTC").dt.tz_convert("Asia/Jakarta").dt.strftime("%d %b %Y | %H:%M WIB")
    df_display["price_fmt"] = df_display["price"].apply(lambda x: f"${x:,.2f}")
    df_display["vol_fmt"] = df_display["volume"].apply(lambda x: f"${x:,.0f}")

    print("\n" + "═" * 78)
    print("     🚀 DATA INGESTION SUCCESSFUL: BITCOIN PRICE & VOLUME MONITOR")
    print("═" * 78)
    print(f" Status API   : 200 OK")
    print(f" Total Rows   : {len(df)} records")
    print(f" Saved Archive: {archive_path}")
    print(f" Updated File : {latest_path}")
    print("─" * 78)
    print(" SAMPLE DATA (HEAD 5):")
    print("┌─────────────┬───────────────────────────┬──────────────────┬─────────────────────┐")
    print("│ Waktu (UTC) │         Waktu (WIB)       │   Harga BTC (USD) │ 24h Volume (USD)    │")
    print("├─────────────┼───────────────────────────┼──────────────────┼─────────────────────┤")

    for _, row in df_display.head(5).iterrows():
        utc = row["utc"].center(11)
        wib = row["wib"].center(25)
        price = row["price_fmt"].rjust(16)
        vol = row["vol_fmt"].rjust(19)
        print(f"│ {utc} │ {wib} │ {price} │ {vol} │")

    print("└─────────────┴───────────────────────────┴──────────────────┴─────────────────────┘")
    print("═" * 78 + "\n")

    return df


if __name__ == "__main__":
    result = fetch_bitcoin_data()
    if result is None:
        sys.exit(1)