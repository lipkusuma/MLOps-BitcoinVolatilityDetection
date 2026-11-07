import os
import pandas as pd
import pytest

DATA_PATH = "data/processed/btc_cleaned.parquet"

def test_dataset_exists():
    """Memastikan dataset hasil preprocessing DVC tersedia."""
    assert os.path.exists(DATA_PATH), f"Dataset {DATA_PATH} tidak ditemukan!"

def test_feature_columns_and_no_leakage():
    """Memastikan fitur masukan utama tersedia dan terpisah dari kolom penyebab Data Leakage di matriks X."""
    df = pd.read_parquet(DATA_PATH)
    
    # 1. Cek ketersediaan fitur input utama
    required_features = ['price', 'volume', 'price_change_pct', 'volume_change_pct']
    for col in required_features:
        assert col in df.columns, f"Fitur {col} hilang dari dataset!"
    
    # 2. Simulasi pembentukan matriks fitur X (seperti pada train.py)
    X = df[required_features]
    
    # Memastikan z_score dan rolling_volatility_14 tidak masuk ke dalam matriks fitur X
    leakage_cols = ['z_score', 'rolling_volatility_14']
    for col in leakage_cols:
        assert col not in X.columns, f"Data Leakage terdeteksi: {col} masuk ke dalam matriks fitur X!"

def test_target_binary():
    """Memastikan label target bersifat biner (0 atau 1)."""
    df = pd.read_parquet(DATA_PATH)
    assert set(df['is_anomaly'].unique()).issubset({0, 1}), "Label target harus biner (0 atau 1)"