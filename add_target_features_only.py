#!/usr/bin/env python3
"""
Add target column to training CSV using only the 8 RF features.
No water_level_m or flood records needed.
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path


# Feature columns (must match RF_FEATURES in config.py)
RF_FEATURES = ['R1', 'R3', 'R7', 'rainy_days', 'TMAX', 'TMIN', 'TideMax', 'TideMin']


def compute_target_from_features(row):
    """
    Composite risk scoring using only the 8 RF features.
    Returns: 0=Low, 1=Medium, 2=High
    """
    score = 0.0
    
    # R1: 1-day precipitation (0-1.5 points)
    r1 = row.get('R1', 0)
    if r1 > 50:
        score += 1.5
    elif r1 > 30:
        score += 1.0
    elif r1 > 15:
        score += 0.5
    
    # R3: 3-day precipitation (0-2 points)
    r3 = row.get('R3', 0)
    if r3 > 100:
        score += 2.0
    elif r3 > 50:
        score += 1.5
    elif r3 > 25:
        score += 1.0
    elif r3 > 10:
        score += 0.5
    
    # R7: 7-day precipitation (0-2.5 points) - strongest predictor
    r7 = row.get('R7', 0)
    if r7 > 200:
        score += 2.5
    elif r7 > 150:
        score += 2.0
    elif r7 > 100:
        score += 1.5
    elif r7 > 50:
        score += 1.0
    elif r7 > 25:
        score += 0.5
    
    # rainy_days: consecutive wet days (0-1.5 points)
    rd = row.get('rainy_days', 0)
    if rd >= 6:
        score += 1.5
    elif rd >= 4:
        score += 1.0
    elif rd >= 2:
        score += 0.5
    
    # TMAX: high temperature (0-0.5 points)
    tmax = row.get('TMAX', 0)
    if tmax > 36:
        score += 0.5
    elif tmax > 34:
        score += 0.3
    
    # TMIN: high minimum temp = humid/unstable (0-0.5 points)
    tmin = row.get('TMIN', 0)
    if tmin > 28:
        score += 0.5
    elif tmin > 26:
        score += 0.3
    
    # TideMax: high tide (0-1.5 points)
    tide_max = row.get('TideMax', 0)
    if tide_max > 1.8:
        score += 1.5
    elif tide_max > 1.5:
        score += 1.0
    elif tide_max > 1.0:
        score += 0.5
    
    # TideMin: high minimum tide = less drainage (0-1 point)
    tide_min = row.get('TideMin', 0)
    if tide_min > 1.0:
        score += 1.0
    elif tide_min > 0.5:
        score += 0.5
    
    # Map score to classes (adjust thresholds based on your data distribution)
    if score >= 6.0:
        return 2  # High
    elif score >= 3.0:
        return 1  # Medium
    else:
        return 0  # Low


def compute_target_percentile_based(row, feature_stats):
    """
    Alternative: Percentile-based labeling using feature percentiles.
    More data-driven, less arbitrary thresholds.
    """
    score = 0.0
    
    # Use percentiles of each feature in the dataset
    for feat, weight in [
        ('R7', 0.30),      # 7-day rain - most important
        ('R3', 0.20),      # 3-day rain
        ('R1', 0.15),      # 1-day rain
        ('rainy_days', 0.10),
        ('TideMax', 0.10),
        ('TideMin', 0.05),
        ('TMAX', 0.05),
        ('TMIN', 0.05),
    ]:
        val = row.get(feat, 0)
        pct = feature_stats[feat]['pct_75']  # 75th percentile as threshold
        if val > feature_stats[feat]['pct_90']:
            score += weight * 3
        elif val > feature_stats[feat]['pct_75']:
            score += weight * 2
        elif val > feature_stats[feat]['pct_50']:
            score += weight * 1
    
    if score >= 1.5:
        return 2
    elif score >= 0.7:
        return 1
    else:
        return 0


def add_target_column(input_csv, output_csv, method='composite'):
    """
    Add target column to CSV using only the 8 RF features.
    
    Args:
        input_csv: Path to input CSV with 8 features
        output_csv: Path to output CSV
        method: 'composite' (threshold-based) or 'percentile' (data-driven)
    """
    print(f"Reading {input_csv}...")
    df = pd.read_csv(input_csv)
    print(f"  Rows: {len(df)}, Columns: {list(df.columns)}")
    
    # Validate required features
    missing = [c for c in RF_FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required feature columns: {missing}")
    
    print(f"Computing target using '{method}' method...")
    
    if method == 'composite':
        df['target'] = df.apply(compute_target_from_features, axis=1)
    elif method == 'percentile':
        # Pre-compute feature statistics
        feature_stats = {}
        for feat in RF_FEATURES:
            feature_stats[feat] = {
                'pct_50': df[feat].quantile(0.50),
                'pct_75': df[feat].quantile(0.75),
                'pct_90': df[feat].quantile(0.90),
            }
        df['target'] = df.apply(lambda r: compute_target_percentile_based(r, feature_stats), axis=1)
    else:
        raise ValueError(f"Unknown method: {method}")
    
    # Show distribution
    dist = df['target'].value_counts().sort_index()
    labels = {0: 'Low', 1: 'Medium', 2: 'High'}
    print("\nTarget distribution:")
    for val, count in dist.items():
        print(f"  {labels[val]} ({val}): {count} ({count/len(df)*100:.1f}%)")
    
    # Save
    df.to_csv(output_csv, index=False)
    print(f"\nSaved to {output_csv}")
    
    # Show sample
    print("\nSample rows:")
    sample_cols = RF_FEATURES + ['target']
    print(df[sample_cols].head(10).to_string())


def main():
    parser = argparse.ArgumentParser(description='Add target column using only 8 RF features')
    parser.add_argument('--input', '-i', required=True, help='Input CSV with 8 features')
    parser.add_argument('--output', '-o', required=True, help='Output CSV with target')
    parser.add_argument('--method', '-m', choices=['composite', 'percentile'], 
                       default='composite', help='Labeling method')
    
    args = parser.parse_args()
    
    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}")
        return 1
    
    try:
        add_target_column(args.input, args.output, args.method)
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    exit(main())