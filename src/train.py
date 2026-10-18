import os
import sys
import warnings
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Abaikan UserWarning bawaan dari MLflow schema inference
warnings.filterwarnings("ignore", category=UserWarning)

import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)

def parse_args():
    parser = argparse.ArgumentParser(description="MLflow Experiment Tracking - Bitcoin Volatility Detection")
    parser.add_argument("--n_estimators", type=int, default=100, help="Jumlah pohon dalam Random Forest")
    parser.add_argument("--max_depth", type=int, default=6, help="Kedalaman maksimum pohon")
    parser.add_argument("--min_samples_split", type=int, default=5, help="Jumlah sampel minimum untuk split node")
    parser.add_argument("--random_state", type=int, default=42, help="Seed untuk reproduksibilitas")
    parser.add_argument("--experiment_name", type=str, default="Bitcoin_Volatility_Detection", help="Nama Eksperimen MLflow")
    parser.add_argument("--run_name", type=str, default="rf_run", help="Nama spesifik untuk run")
    return parser.parse_args()

def load_data(filepath="data/processed/btc_cleaned.parquet"):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Dataset {filepath} tidak ditemukan. Pastikan 'python src/preprocess.py' sudah dijalankan!")
    
    df = pd.read_parquet(filepath)
    
    # Deteksi kolom target biner
    target_col = "is_anomaly" if "is_anomaly" in df.columns else "is_high_volatility"
    if target_col not in df.columns:
        raise KeyError("Kolom target ('is_anomaly' atau 'is_high_volatility') tidak ditemukan!")
        
    # 🚨 PENCEGAHAN DATA LEAKAGE:
    # Buang z_score dan rolling_volatility_14 karena merupakan variabel pembentuk target secara langsung
    leakage_cols = [target_col, "timestamp", "datetime", "z_score", "rolling_volatility_14", "rolling_volatility"]
    
    feature_cols = [c for c in df.columns if c not in leakage_cols and np.issubdtype(df[c].dtype, np.number)]
    
    # Konversi seluruh fitur numerik ke float64
    X = df[feature_cols].astype(np.float64)
    y = df[target_col]
    
    return X, y, feature_cols

def plot_confusion_matrix(y_true, y_pred, output_path="confusion_matrix.png"):
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=["Normal (0)", "Anomaly (1)"], yticklabels=["Normal (0)", "Anomaly (1)"])
    plt.xlabel("Predicted Label")
    plt.ylabel("True Label")
    plt.title("Confusion Matrix - Bitcoin Volatility Detection")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def main():
    args = parse_args()
    
    # Set Tracking Experiment MLflow
    mlflow.set_experiment(args.experiment_name)
    
    # Load & Split Data
    X, y, feature_cols = load_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=args.random_state, stratify=y
    )
    
    # Mulai logging dengan MLflow
    with mlflow.start_run(run_name=args.run_name):
        # 1. Logging Tags Metadata
        mlflow.set_tags({
            "author": "Alif Kusuma Fauzan",
            "nim": "245150201111051",
            "model_family": "Random Forest",
            "dataset_version": "v2.0_DVC",
            "task": "Binary Classification"
        })
        
        # 2. Logging Hyperparameters
        mlflow.log_params({
            "n_estimators": args.n_estimators,
            "max_depth": args.max_depth,
            "min_samples_split": args.min_samples_split,
            "random_state": args.random_state,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "num_features": len(feature_cols)
        })
        
        # 3. Model Training
        model = RandomForestClassifier(
            n_estimators=args.n_estimators,
            max_depth=args.max_depth,
            min_samples_split=args.min_samples_split,
            random_state=args.random_state
        )
        model.fit(X_train, y_train)
        
        # 4. Prediksi & Evaluasi
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred
        
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        try:
            roc_auc = roc_auc_score(y_test, y_proba)
        except Exception:
            roc_auc = 0.5
            
        # 5. Logging Metrics
        mlflow.log_metrics({
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1_score": f1,
            "roc_auc": roc_auc
        })
        
        # 6. Generate & Logging Visual Artifacts
        plot_confusion_matrix(y_test, y_pred, "confusion_matrix.png")
        mlflow.log_artifact("confusion_matrix.png")
        if os.path.exists("confusion_matrix.png"):
            os.remove("confusion_matrix.png")
            
        # 7. Logging Sklearn Model Artifact
        input_example = X_train.iloc[:5]
        mlflow.sklearn.log_model(
            sk_model=model,
            name="model",
            input_example=input_example,
            skops_trusted_types=["sklearn.tree._tree.Tree"]
        )
        
        print(f"✅ Executed Run [{args.run_name}] successfully!")
        print(f"   Accuracy: {acc:.4f} | Precision: {prec:.4f} | Recall: {rec:.4f} | F1-Score: {f1:.4f} | ROC-AUC: {roc_auc:.4f}")

if __name__ == "__main__":
    main()