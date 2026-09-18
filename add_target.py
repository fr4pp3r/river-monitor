#!/usr/bin/env python3
"""
Add target column to training CSV based on historical rain/tide data.
Uses composite risk scoring since no flood records available.
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path


def compute_target_composite(row, critical_level_m=7.5):
    """
    Composite risk scoring based on water level, rainfall, and tide.
    Returns: 0=Low, 1=Medium, 2=High
    """
    score = 0
    
    # Water level contribution (0-3 points)
    water_level = row.get('water_level_m', 0)
    pct = water_level / critical_level_m
    if pct >= 1.0:
        score += 3
    elif pct >= 0.6:
        score += 2
    elif pct >= 0.4:
        score += 1
    
    # 7-day rainfall (R7) contribution (0-2 points)
    r7 = row.get('R7', row.get('precip_7d', 0))
    if r7 > 150:
        score += 2
    elif r7 > 75:
        score += 1
    
    # 3-day rainfall (R3) contribution (0-1 point)
    r3 = row.get('R3', row.get('precip_3d', 0))
    if r3 > 50:
        score += 1
    
    # 1-day rainfall (R1) contribution (0-1 point)
    r1 = row.get('R1', row.get('precipitation_mm', 0))
    if r1 > 30:
        score += 1
    
    # Rainy days contribution (0-1 point)
    rain_days = row.get('rain_days', 0)
    if rain_days >= 5:
        score += 1
    elif rain_days >= 3:
        score += 0.5
    
    # Tide contribution (0-1 point)
    tide_max = row.get('TideMax', row.get('tide_max_m', 0))
    if tide_max > 1.5:
        score += 1
    elif tide_max > 1.0:
        score += 0.5
    
    # Temperature contribution (0-0.5 point) - high temp = more evaporation but also more storms
    tmax = row.get('TMAX', row.get('temperature_max_c', 0))
    if tmax > 35:
        score += 0.5
    
    # Map score to classes
    if score >= 5.0:
        return 2  # High
    elif score >= 2.5:
        return 1  # Medium
    else:
        return 0  # Low


def compute_target_percentile(row, critical_level_m=7.5):
    """
    Alternative: Percentile-based labeling using water level percentiles.
    """
    water_level = row.get('water_level_m', 0)
    pct = water_level / critical_level_m
    
    if pct >= 0.8:      # Top 20%
        return 2
    elif pct >= 0.5:    # Middle 30%
        return 1
    else:               # Bottom 50%
        return 0


def add_target_column(input_csv, output_csv, method='composite', critical_level=7.5):
    """
    Add target column to CSV.
    
    Args:
        input_csv: Path to input CSV
        output_csv: Path to output CSV
        method: 'composite' or 'percentile'
        critical_level: Critical water level in meters
    """
    print(f"Reading {input_csv}...")
    df = pd.read_csv(input_csv)
    print(f"  Rows: {len(df)}, Columns: {list(df.columns)}")
    
    # Ensure required columns exist
    required = ['water_level_m']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # Compute target
    print(f"Computing target using '{method}' method...")
    if method == 'composite':
        df['target'] = df.apply(lambda r: compute_target_composite(r, critical_level), axis=1)
    elif method == 'percentile':
        df['target'] = df.apply(lambda r: compute_target_percentile(r, critical_level), axis=1)
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
    sample_cols = ['date', 'water_level_m', 'R1', 'R3', 'R7', 'rain_days', 
                   'TMAX', 'TMIN', 'TideMax', 'target']
    available = [c for c in sample_cols if c in df.columns]
    print(df[available].head(10).to_string())


def main():
    parser = argparse.ArgumentParser(description='Add target column to training CSV')
    parser.add_argument('--input', '-i', required=True, help='Input CSV file')
    parser.add_argument('--output', '-o', required=True, help='Output CSV file')
    parser.add_argument('--method', '-m', choices=['composite', 'percentile'], 
                       default='composite', help='Labeling method')
    parser.add_argument('--critical-level', '-c', type=float, default=7.5,
                       help='Critical water level in meters')
    
    args = parser.parse_args()
    
    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}")
        return 1
    
    try:
        add_target_column(args.input, args.output, args.method, args.critical_level)
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    exit(main())