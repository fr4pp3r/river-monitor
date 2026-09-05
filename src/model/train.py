"""
Model Training for River Monitor AI System
Trains a Random Forest classifier for flood risk prediction
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib
import os

from src.config import (
    MODEL_PATH, MODEL_N_ESTIMATORS, MODEL_MAX_DEPTH,
    MODEL_RANDOM_STATE, MODEL_TEST_SIZE,
    RF_CLASSES
)
from src.model.preprocess import (
    preprocess_training_data, preprocess_training_data_new, save_scaler, load_scaler
)


def train_model(
    water_level_csv: str,
    weather_csv: str,
    model_path: str = MODEL_PATH,
    n_estimators: int = MODEL_N_ESTIMATORS,
    max_depth: int = MODEL_MAX_DEPTH,
    random_state: int = MODEL_RANDOM_STATE,
    test_size: float = MODEL_TEST_SIZE
) -> Tuple[RandomForestClassifier, float, dict]:
    """
    Train a Random Forest classifier for flood risk prediction (legacy)
    
    Args:
        water_level_csv: Path to water level CSV file
        weather_csv: Path to weather data CSV file
        model_path: Path to save the trained model
        n_estimators: Number of trees in the forest
        max_depth: Maximum depth of the trees
        random_state: Random seed for reproducibility
        test_size: Fraction of data to use for testing
    
    Returns:
        Tuple of (trained_model, test_accuracy, classification_report_dict)
    """
    print("Starting model training (legacy)...")
    print(f"Loading data from: {water_level_csv}, {weather_csv}")
    
    # Preprocess data
    X, y, scaler = preprocess_training_data(water_level_csv, weather_csv)
    
    print(f"Dataset shape: {X.shape}")
    print(f"Feature columns: {list(X.columns)}")
    print(f"Class distribution:\n{y.value_counts()}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    
    print(f"\nTraining set: {X_train.shape[0]} samples")
    print(f"Test set: {X_test.shape[0]} samples")
    
    # Train model
    print("\nTraining Random Forest classifier...")
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
        class_weight='balanced',  # Handle class imbalance
        n_jobs=-1  # Use all CPU cores
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate model
    print("\nEvaluating model...")
    y_pred = model.predict(X_test)
    
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Test Accuracy: {accuracy:.4f}")
    
    # Classification report
    report = classification_report(y_test, y_pred, 
                                   target_names=['normal', 'alert', 'alarm', 'critical'],
                                   output_dict=True)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, 
                               target_names=['normal', 'alert', 'alarm', 'critical']))
    
    # Save model and scaler
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model, model_path)
    save_scaler(scaler, os.path.join(os.path.dirname(model_path), "scaler.pkl"))
    
    print(f"\nModel saved to {model_path}")
    print(f"Scaler saved to {os.path.join(os.path.dirname(model_path), 'scaler.pkl')}")
    
    return model, accuracy, report


def train_model_new(
    csv_path: str,
    model_path: str = MODEL_PATH,
    n_estimators: int = MODEL_N_ESTIMATORS,
    max_depth: int = MODEL_MAX_DEPTH,
    random_state: int = MODEL_RANDOM_STATE,
    test_size: float = MODEL_TEST_SIZE
) -> Tuple[RandomForestClassifier, float, dict]:
    """
    Train a Random Forest classifier for flood propensity prediction (new 7-feature model)
    
    Args:
        csv_path: Path to training CSV with columns: R1, R3, R7, rainy_days, TMAX, TMIN, TideMax, target
        model_path: Path to save the trained model
        n_estimators: Number of trees in the forest
        max_depth: Maximum depth of the trees
        random_state: Random seed for reproducibility
        test_size: Fraction of data to use for testing
    
    Returns:
        Tuple of (trained_model, test_accuracy, classification_report_dict)
    """
    print("Starting model training (new 7-feature model)...")
    print(f"Loading data from: {csv_path}")
    
    # Preprocess data
    X, y, scaler = preprocess_training_data_new(csv_path)
    
    print(f"Dataset shape: {X.shape}")
    print(f"Feature columns: {list(X.columns)}")
    print(f"Class distribution:\n{y.value_counts().sort_index()}")
    print(f"Class mapping: {RF_CLASSES}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    
    print(f"\nTraining set: {X_train.shape[0]} samples")
    print(f"Test set: {X_test.shape[0]} samples")
    
    # Train model
    print("\nTraining Random Forest classifier...")
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
        class_weight='balanced',  # Handle class imbalance
        n_jobs=-1  # Use all CPU cores
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate model
    print("\nEvaluating model...")
    y_pred = model.predict(X_test)
    
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Test Accuracy: {accuracy:.4f}")
    
    # Classification report
    target_names = [RF_CLASSES[i] for i in sorted(RF_CLASSES.keys())]
    report = classification_report(y_test, y_pred, 
                                   target_names=target_names,
                                   output_dict=True)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, 
                               target_names=target_names))
    
    # Confusion Matrix
    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(y_test, y_pred)
    print("\nConfusion Matrix:")
    print("                 Predicted")
    print("              Low  Medium  High")
    for i, actual in enumerate(target_names):
        row = cm[i]
        print(f"Actual {actual:6s}  {row[0]:4d}  {row[1]:6d}  {row[2]:4d}")
    
    # Per-class metrics
    print("\nPer-Class Metrics:")
    for i, class_name in enumerate(target_names):
        tp = cm[i, i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp
        tn = cm.sum() - tp - fp - fn
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        
        print(f"  {class_name:6s}: Precision={precision:.4f}, Recall={recall:.4f}, "
              f"F1={f1:.4f}, Specificity={specificity:.4f}")
    
    # Macro and weighted averages
    macro_precision = sum(report[c]['precision'] for c in target_names) / len(target_names)
    macro_recall = sum(report[c]['recall'] for c in target_names) / len(target_names)
    macro_f1 = sum(report[c]['f1-score'] for c in target_names) / len(target_names)
    
    weighted_precision = sum(report[c]['precision'] * report[c]['support'] for c in target_names) / sum(report[c]['support'] for c in target_names)
    weighted_recall = sum(report[c]['recall'] * report[c]['support'] for c in target_names) / sum(report[c]['support'] for c in target_names)
    weighted_f1 = sum(report[c]['f1-score'] * report[c]['support'] for c in target_names) / sum(report[c]['support'] for c in target_names)
    
    print(f"\nMacro Average:    Precision={macro_precision:.4f}, Recall={macro_recall:.4f}, F1={macro_f1:.4f}")
    print(f"Weighted Average: Precision={weighted_precision:.4f}, Recall={weighted_recall:.4f}, F1={weighted_f1:.4f}")
    
    # Save model and scaler
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model, model_path)
    save_scaler(scaler, os.path.join(os.path.dirname(model_path), "scaler.pkl"))
    
    print(f"\nModel saved to {model_path}")
    print(f"Scaler saved to {os.path.join(os.path.dirname(model_path), 'scaler.pkl')}")
    
    return model, accuracy, report


def load_model(model_path: str = MODEL_PATH) -> RandomForestClassifier:
    """
    Load a trained model from file
    
    Args:
        model_path: Path to the model file
    
    Returns:
        Loaded RandomForestClassifier
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    return joblib.load(model_path)


def get_feature_importance(model: RandomForestClassifier) -> pd.DataFrame:
    """
    Get feature importance from the trained model
    
    Args:
        model: Trained RandomForestClassifier
    
    Returns:
        DataFrame with feature names and importance scores
    """
    if not hasattr(model, 'feature_importances_'):
        raise ValueError("Model has no feature_importances_ attribute")
    
    # Use RF_FEATURES from config for proper feature names
    from src.config import RF_FEATURES
    feature_names = RF_FEATURES
    
    return pd.DataFrame({
        'feature': feature_names,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)


def validate_model(model_path: str, water_level_csv: str, weather_csv: str) -> dict:
    """
    Validate a trained model on new data (legacy)
    
    Args:
        model_path: Path to the model file
        water_level_csv: Path to water level CSV
        weather_csv: Path to weather CSV
    
    Returns:
        Dictionary with validation metrics
    """
    # Load model
    model = load_model(model_path)
    
    # Preprocess data
    X, y, _ = preprocess_training_data(water_level_csv, weather_csv)
    
    # Predict
    y_pred = model.predict(X)
    
    # Calculate metrics
    accuracy = accuracy_score(y, y_pred)
    report = classification_report(y, y_pred, 
                                   target_names=['normal', 'alert', 'alarm', 'critical'],
                                   output_dict=True)
    
    return {
        'accuracy': accuracy,
        'classification_report': report,
        'predictions': y_pred,
        'actual': y.values
    }


def validate_model_new(model_path: str, csv_path: str) -> dict:
    """
    Validate a trained model on new data (new 7-feature model)
    
    Args:
        model_path: Path to the model file
        csv_path: Path to training CSV
    
    Returns:
        Dictionary with validation metrics
    """
    # Load model
    model = load_model(model_path)
    
    # Preprocess data
    X, y, _ = preprocess_training_data_new(csv_path)
    
    # Predict
    y_pred = model.predict(X)
    
    # Calculate metrics
    accuracy = accuracy_score(y, y_pred)
    target_names = [RF_CLASSES[i] for i in sorted(RF_CLASSES.keys())]
    report = classification_report(y, y_pred, 
                                   target_names=target_names,
                                   output_dict=True)
    
    return {
        'accuracy': accuracy,
        'classification_report': report,
        'predictions': y_pred,
        'actual': y.values
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Train flood risk prediction model')
    parser.add_argument('--mode', type=str, choices=['legacy', 'new'], default='new',
                       help='Training mode: legacy (water+weather CSV) or new (single CSV with target)')
    parser.add_argument('--water', type=str, 
                       help='Path to water level CSV file (legacy mode)')
    parser.add_argument('--weather', type=str,
                       help='Path to weather data CSV file (legacy mode)')
    parser.add_argument('--csv', type=str,
                       help='Path to training CSV file (new mode)')
    parser.add_argument('--output', type=str, default=MODEL_PATH,
                       help='Path to save the trained model')
    
    args = parser.parse_args()
    
    if args.mode == 'legacy':
        if not args.water or not args.weather:
            parser.error("Legacy mode requires --water and --weather arguments")
        model, accuracy, report = train_model(
            args.water, 
            args.weather, 
            model_path=args.output
        )
    else:
        if not args.csv:
            parser.error("New mode requires --csv argument")
        model, accuracy, report = train_model_new(
            args.csv, 
            model_path=args.output
        )
    
    print(f"\nModel training complete!")
    print(f"Model saved to: {args.output}")
    print(f"Test Accuracy: {accuracy:.4f}")
    
    # Show feature importance
    print("\nFeature Importance:")
    try:
        importance = get_feature_importance(model)
        print(importance.to_string(index=False))
    except Exception as e:
        print(f"Could not get feature importance: {e}")