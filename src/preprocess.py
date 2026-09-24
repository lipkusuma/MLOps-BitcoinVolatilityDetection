"""
Module Prapemrosesan Data dan Feature Engineering.
Menerima data mentah dari data/raw/, melakukan pembersihan, validasi,
ekstraksi fitur volatilitas, dan menyimpan luaran ke format Parquet.
"""

import os
import sys
import pandas as pd


def run_preprocessing(
    input_path: str = "data/raw/btc_raw_latest.csv",
    output_path: str = "data/processed/btc_cleaned.parquet"
) -> pd.DataFrame | None:
    """
    Membersihkan data mentah dan membentuk fitur-fitur pendukung deteksi anomali.
    
    Args:
        input_path (str): Jalur berkas CSV data mentah.
        output_path (str): Jalur berkas Parquet data olahan.
        
    Returns:
        pd.DataFrame | None: DataFrame yang telah dibersihkan atau None jika error.
    """
    if not os.path.exists(input_path):
        print(f"❌ File Input Tidak Ditemukan: {input_path}. Jalankan ingest_data.py terlebih dahulu.")
        return None

    print(f"🔄 Membaca data mentah dari {input_path}...")
    df = pd.read_csv(input_path)

    # 1. Cleaning & Imputation
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    # Penanganan Nilai Hilang
    df["price"] = df["price"].ffill()
    df["volume"] = df["volume"].ffill()

    # 2. Feature Engineering
    df["price_change_pct"] = df["price"].pct_change() * 100
    df["volume_change_pct"] = df["volume"].pct_change() * 100

    # Rolling Volatility 14 periode
    df["rolling_volatility_14"] = df["price_change_pct"].rolling(window=14).std()

    # Perhitungan Z-Score untuk deteksi pencilan
    mean_vol = df["rolling_volatility_14"].mean()
    std_vol = df["rolling_volatility_14"].std()

    if std_vol > 0:
        df["z_score"] = (df["rolling_volatility_14"] - mean_vol) / std_vol
    else:
        df["z_score"] = 0.0

    # Label Target Biner (1 = Anomali, 0 = Normal)
    df["is_anomaly"] = (df["z_score"] > 2.5).astype(int)

    # Menghapus baris NaN di awal akibat kalkulasi window
    df_cleaned = df.dropna().reset_index(drop=True)

    # 3. Export ke Format Parquet
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_cleaned.to_parquet(output_path, index=False, engine="pyarrow")

    # 4. Tampilan Logging Terminal Interaktif (Rapi & Terstruktur)
    df_display = df_cleaned.head(5).copy()
    df_display["time_fmt"] = df_display["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    df_display["price_fmt"] = df_display["price"].apply(lambda x: f"${x:,.2f}")
    df_display["vol_fmt"] = df_display["rolling_volatility_14"].apply(lambda x: f"{x:.4f}")
    df_display["z_fmt"] = df_display["z_score"].apply(lambda x: f"{x:+.2f}")
    df_display["status_fmt"] = df_display["is_anomaly"].apply(lambda x: "🚨 1 (ANOMALY)" if x == 1 else "✅ 0 (NORMAL)")

    print("\n" + "═" * 82)
    print("     ✨ DATA PREPROCESSING & FEATURE ENGINEERING SUCCESSFUL")
    print("═" * 82)
    print(f" Raw Records       : {len(df)} baris")
    print(f" Cleaned Records   : {len(df_cleaned)} baris")
    print(f" Total Anomaly     : {df_cleaned['is_anomaly'].sum()} titik terdeteksi")
    print(f" Saved Output File : {output_path}")
    print("─" * 82)
    print(" SAMPLE PROCESSED DATA (HEAD 5):")
    print("┌──────────────────┬─────────────────┬─────────────┬───────────┬──────────────────┐")
    print("│   Waktu (UTC)    │ Harga BTC (USD) │ Volatility  │  Z-Score  │      Status      │")
    print("├──────────────────┼─────────────────┼─────────────┼───────────┼──────────────────┤")

    for _, row in df_display.iterrows():
        t_str = row["time_fmt"].center(16)
        p_str = row["price_fmt"].rjust(15)
        v_str = row["vol_fmt"].rjust(11)
        z_str = row["z_fmt"].rjust(9)
        s_str = row["status_fmt"].center(16)
        print(f"│ {t_str} │ {p_str} │ {v_str} │ {z_str} │ {s_str} │")

    print("└──────────────────┴─────────────────┴─────────────┴───────────┴──────────────────┘")
    print("═" * 82 + "\n")

    return df_cleaned


if __name__ == "__main__":
    result = run_preprocessing()
    if result is None:
        sys.exit(1)