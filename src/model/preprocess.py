"""
Data Preprocessing for River Monitor AI Model
Handles data cleaning, feature engineering, and preparation for training
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, Optional
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
import os

from src.config import (
    RISK_THRESHOLDS, CRITICAL_LEVEL_M,
    MODEL_RANDOM_STATE, MODEL_TEST_SIZE,
    RF_FEATURES, RF_CLASSES
)


def load_historical_data(water_level_csv: str, weather_csv: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load historical water level and weather data from CSV files
    
    Args:
        water_level_csv: Path to water level CSV file
        weather_csv: Path to weather data CSV file
    
    Returns:
        Tuple of (water_level_df, weather_df)
    """
    # Load water level data
    water_level_df = pd.read_csv(water_level_csv)
    
    # Ensure datetime column exists
    if 'date' in water_level_df.columns:
        water_level_df['timestamp'] = pd.to_datetime(water_level_df['date'])
    elif 'timestamp' in water_level_df.columns:
        water_level_df['timestamp'] = pd.to_datetime(water_level_df['timestamp'])
    else:
        raise ValueError("CSV must have 'date' or 'timestamp' column")
    
    # Load weather data
    weather_df = pd.read_csv(weather_csv)
    
    if 'date' in weather_df.columns:
        weather_df['timestamp'] = pd.to_datetime(weather_df['date'])
    elif 'timestamp' in weather_df.columns:
        weather_df['timestamp'] = pd.to_datetime(weather_df['timestamp'])
    else:
        raise ValueError("Weather CSV must have 'date' or 'timestamp' column")
    
    return water_level_df, weather_df


def load_training_data(csv_path: str) -> pd.DataFrame:
    """
    Load training data from a single CSV with all features and target
    
    Expected columns: R1, R3, R7, rainy_days, TMAX, TMIN, TideMax, target
    Target values: 0=Low, 1=Medium, 2=High
    
    Args:
        csv_path: Path to training CSV file
    
    Returns:
        DataFrame with features and target
    """
    df = pd.read_csv(csv_path)
    
    # Ensure timestamp column exists
    if 'date' in df.columns:
        df['timestamp'] = pd.to_datetime(df['date'])
    elif 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Validate required columns
    required_features = RF_FEATURES + ['target']
    missing = [col for col in required_features if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    return df


def merge_datasets(water_level_df: pd.DataFrame, weather_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge water level and weather data on timestamp
    
    Args:
        water_level_df: Water level DataFrame
        weather_df: Weather DataFrame
    
    Returns:
        Merged DataFrame with all features
    """
    # Set timestamp as index for both
    water_level_df.set_index('timestamp', inplace=True)
    weather_df.set_index('timestamp', inplace=True)
    
    # Resample to daily frequency (if not already)
    water_level_df = water_level_df.resample('D').mean()
    weather_df = weather_df.resample('D').mean()
    
    # Merge on timestamp
    merged_df = pd.merge(
        water_level_df, 
        weather_df, 
        left_index=True, 
        right_index=True,
        how='left'
    )
    
    # Forward fill missing values (carry last known value forward)
    merged_df.ffill(inplace=True)
    
    # Drop rows with missing water level (critical feature)
    merged_df.dropna(subset=['water_level_m'], inplace=True)
    
    return merged_df


def calculate_risk_level(water_level: float) -> str:
    """
    Calculate risk level based on water level and PAGASA thresholds
    
    Args:
        water_level: Current water level in meters
    
    Returns:
        Risk level string: 'normal', 'alert', 'alarm', 'critical'
    """
    # Calculate percentage of critical level
    percentage = water_level / CRITICAL_LEVEL_M
    
    if percentage >= RISK_THRESHOLDS['critical']:
        return 'critical'
    elif percentage >= RISK_THRESHOLDS['alarm']:
        return 'alarm'
    elif percentage >= RISK_THRESHOLDS['alert']:
        return 'alert'
    else:
        return 'normal'


def add_target_variable(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add target variable (risk level) to the dataset
    
    Args:
        df: DataFrame with water_level_m column
    
    Returns:
        DataFrame with added risk_level column
    """
    df['risk_level'] = df['water_level_m'].apply(calculate_risk_level)
    
    # Convert risk level to numerical for training
    risk_mapping = {'normal': 0, 'alert': 1, 'alarm': 2, 'critical': 3}
    df['risk_level_num'] = df['risk_level'].map(risk_mapping)
    
    return df


def create_rf_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create RF model features from daily data
    
    Features: R1, R3, R7, rainy_days, TMAX, TMIN, TideMax
    
    Args:
        df: DataFrame with daily weather data (precipitation_mm, temperature_max_c, 
            temperature_min_c, tide_max_m)
    
    Returns:
        DataFrame with RF features
    """
    # Ensure daily frequency at 1:00 AM
    df = df.resample('D', offset='1H').mean()
    
    # R1: 1-day precipitation
    df['R1'] = df['precipitation_mm']
    
    # R3: 3-day precipitation sum
    df['R3'] = df['precipitation_mm'].rolling(window=3, min_periods=1).sum()
    
    # R7: 7-day precipitation sum
    df['R7'] = df['precipitation_mm'].rolling(window=7, min_periods=1).sum()
    
    # rainy_days: count of days with precipitation > 0 in last 7 days
    df['rainy_days'] = (df['precipitation_mm'] > 0).rolling(window=7, min_periods=1).sum()
    
    # TMAX: daily max temperature
    df['TMAX'] = df['temperature_max_c']
    
    # TMIN: daily min temperature
    df['TMIN'] = df['temperature_min_c']
    
    # TideMax: daily max tide level
    df['TideMax'] = df['tide_max_m']
    
    # TideMin: daily min tide level
    df['TideMin'] = df['tide_min_m']
    
    # Drop rows with NaN values in features
    df.dropna(subset=RF_FEATURES, inplace=True)
    
    return df


def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create features for the prediction model (legacy - for backward compatibility)
    
    Args:
        df: DataFrame with raw data
    
    Returns:
        DataFrame with engineered features
    """
    # Resample to daily frequency at 1:00 AM for model compatibility
    df = df.resample('D', offset='1H').mean()
    
    # Create time-based features
    df['month'] = df.index.month
    df['day'] = df.index.day
    df['day_of_year'] = df.index.dayofyear
    
    # Create rolling averages for water level
    df['level_7d_avg'] = df['water_level_m'].rolling(window=7, min_periods=1).mean()
    df['level_30d_avg'] = df['water_level_m'].rolling(window=30, min_periods=1).mean()
    
    # Create water level change features (1-day and 7-day changes)
    df['level_change_1d'] = df['water_level_m'].diff(1)
    df['level_change_7d'] = df['water_level_m'].diff(7)
    
    # Create pressure trend feature
    if 'pressure_hpa' in df.columns:
        df['pressure_trend'] = df['pressure_hpa'].diff(1)
    
    # Create aggregated precipitation feature (7-day and 30-day)
    if 'precipitation_mm' in df.columns:
        df['precip_7d'] = df['precipitation_mm'].rolling(window=7, min_periods=1).sum()
        df['precip_30d'] = df['precipitation_mm'].rolling(window=30, min_periods=1).sum()
    
    # Create rainfall features (if available)
    if 'rainfall_mm' in df.columns:
        df['rainfall_7d'] = df['rainfall_mm'].rolling(window=7, min_periods=1).sum()
        df['rainfall_30d'] = df['rainfall_mm'].rolling(window=30, min_periods=1).sum()
    
    # Drop rows with NaN values in features
    df.dropna(inplace=True)
    
    return df


def select_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Select features and target for model training
    
    Args:
        df: DataFrame with all features
    
    Returns:
        Tuple of (features_df, target_series)
    """
    # Use RF features for new model
    available_features = [col for col in RF_FEATURES if col in df.columns]
    
    if len(available_features) == len(RF_FEATURES):
        # New model with 7 features
        X = df[RF_FEATURES]
    else:
        # Legacy model with old features
        feature_columns = [
            'water_level_m',
            'level_7d_avg',
            'level_30d_avg',
            'level_change_1d',
            'level_change_7d',
            'rainfall_mm',
            'rainfall_7d',
            'rainfall_30d',
            'precipitation_mm',
            'precip_7d',
            'precip_30d',
            'pressure_hpa',
            'pressure_trend',
            'temperature_c',
            'humidity_percent',
            'wind_speed_ms',
            'month',
            'day',
            'day_of_year'
        ]
        available_features = [col for col in feature_columns if col in df.columns]
        X = df[available_features]
    
    # Target
    if 'target' in df.columns:
        y = df['target']
    elif 'risk_level_num' in df.columns:
        y = df['risk_level_num']
    else:
        raise ValueError("No target column found (expected 'target' or 'risk_level_num')")
    
    return X, y


def scale_features(X: pd.DataFrame, scaler: Optional[StandardScaler] = None, fit: bool = True) -> Tuple[pd.DataFrame, StandardScaler]:
    """
    Scale features using StandardScaler
    
    Args:
        X: Feature DataFrame
        scaler: Optional existing scaler
        fit: Whether to fit the scaler
    
    Returns:
        Tuple of (scaled_X, scaler)
    """
    if scaler is None:
        scaler = StandardScaler()
    
    if fit:
        X_scaled = scaler.fit_transform(X)
    else:
        X_scaled = scaler.transform(X)
    
    return pd.DataFrame(X_scaled, columns=X.columns), scaler


def preprocess_training_data(water_level_csv: str, weather_csv: str) -> Tuple[pd.DataFrame, pd.Series, StandardScaler]:
    """
    Complete preprocessing pipeline for training data (legacy)
    
    Args:
        water_level_csv: Path to water level CSV
        weather_csv: Path to weather CSV
    
    Returns:
        Tuple of (X_scaled, y, scaler)
    """
    # Load data
    water_df, weather_df = load_historical_data(water_level_csv, weather_csv)
    
    # Merge datasets
    merged_df = merge_datasets(water_df, weather_df)
    
    # Add target variable
    merged_df = add_target_variable(merged_df)
    
    # Create features
    merged_df = create_features(merged_df)
    
    # Select features and target
    X, y = select_features(merged_df)
    
    # Scale features
    X_scaled, scaler = scale_features(X, fit=True)
    
    return X_scaled, y, scaler


def preprocess_training_data_new(csv_path: str) -> Tuple[pd.DataFrame, pd.Series, StandardScaler]:
    """
    New preprocessing pipeline for training data with RF features
    
    Args:
        csv_path: Path to training CSV with R1,R3,R7,rainy_days,TMAX,TMIN,TideMax,target
    
    Returns:
        Tuple of (X_scaled, y, scaler)
    """
    # Load data
    df = load_training_data(csv_path)
    
    # Select features and target
    X, y = select_features(df)
    
    # Scale features
    X_scaled, scaler = scale_features(X, fit=True)
    
    return X_scaled, y, scaler


def save_scaler(scaler: StandardScaler, path: str = "data/models/scaler.pkl"):
    """Save scaler to file"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(scaler, path)
    print(f"Scaler saved to {path}")


def load_scaler(path: str = "data/models/scaler.pkl") -> StandardScaler:
    """Load scaler from file"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Scaler file not found: {path}")
    return joblib.load(path)


def preprocess_for_prediction(data: Dict, scaler: StandardScaler) -> pd.DataFrame:
    """
    Preprocess real-time data for prediction
    
    Args:
        data: Dictionary with current data
        scaler: Fitted scaler
    
    Returns:
        Scaled feature DataFrame
    """
    # Create DataFrame from input data
    input_df = pd.DataFrame([data])
    
    # Add timestamp for feature engineering
    input_df['timestamp'] = pd.to_datetime(data.get('timestamp', datetime.now()))
    input_df.set_index('timestamp', inplace=True)
    
    # Create features (reusing the same logic as training)
    input_df = create_features(input_df)
    
    # Select features
    X, _ = select_features(input_df)
    
    # Scale features
    X_scaled, _ = scale_features(X, scaler=scaler, fit=False)
    
    return X_scaled


def preprocess_for_prediction_new(data: Dict, scaler: StandardScaler) -> pd.DataFrame:
    """
    Preprocess real-time data for new RF model prediction
    
    Args:
        data: Dictionary with RF features (R1, R3, R7, rainy_days, TMAX, TMIN, TideMax)
        scaler: Fitted scaler
    
    Returns:
        Scaled feature DataFrame
    """
    # Create DataFrame from input data
    input_df = pd.DataFrame([data])
    
    # Select only RF features
    X = input_df[RF_FEATURES]
    
    # Scale features
    X_scaled, _ = scale_features(X, scaler=scaler, fit=False)
    
    return X_scaled


if __name__ == "__main__":
    # Example usage
    print("Data Preprocessing Module")
    print("Use train.py to preprocess and train the model")
    
    # Test risk level calculation
    test_levels = [0, 3.0, 4.5, 6.0, 7.5]
    print("\nRisk Level Test:")
    for level in test_levels:
        risk = calculate_risk_level(level)
        percentage = (level / CRITICAL_LEVEL_M) * 100
        print(f"  {level:.1f}m ({percentage:.0f}%) -> {risk}")