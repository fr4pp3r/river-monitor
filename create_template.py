#!/usr/bin/env python3
"""
Create a sample training CSV template with the required columns.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Generate sample data for 5 years (daily)
np.random.seed(42)
n_days = 5 * 365
dates = [datetime(2019, 1, 1) + timedelta(days=i) for i in range(n_days)]

# Simulate realistic data
data = {
    'date': [d.strftime('%Y-%m-%d') for d in dates],
    'water_level_m': np.random.normal(2.5, 1.2, n_days).clip(0, 7.5),
    'precipitation_mm': np.random.exponential(5, n_days).clip(0, 100),
    'temperature_max_c': np.random.normal(32, 3, n_days).clip(25, 40),
    'temperature_min_c': np.random.normal(24, 2, n_days).clip(20, 30),
    'tide_max_m': np.random.uniform(0.2, 2.0, n_days),
    'tide_min_m': np.random.uniform(0.0, 1.0, n_days),
}

df = pd.DataFrame(data)

# Compute derived features
df['R1'] = df['precipitation_mm']
df['R3'] = df['precipitation_mm'].rolling(3, min_periods=1).sum()
df['R7'] = df['precipitation_mm'].rolling(7, min_periods=1).sum()
df['rainy_days'] = (df['precipitation_mm'] > 0).rolling(7, min_periods=1).sum()
df['TMAX'] = df['temperature_max_c']
df['TMIN'] = df['temperature_min_c']
df['TideMax'] = df['tide_max_m'].rolling(7, min_periods=1).max()
df['TideMin'] = df['tide_min_m'].rolling(7, min_periods=1).min()

# Save template
df.to_csv('training_template.csv', index=False)
print("Created training_template.csv")
print(f"Rows: {len(df)}")
print(f"Columns: {list(df.columns)}")
print("\nFirst 5 rows:")
print(df.head())
print("\nRequired columns for training:")
print("  R1, R3, R7, rainy_days, TMAX, TMIN, TideMax, TideMin, target")
print("\nAfter adding target column, use:")
print("  python src/model/train.py --mode new --csv training_data.csv --output data/models/rf_model.pkl")