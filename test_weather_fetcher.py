#!/usr/bin/env python3
"""
Test script for Open-Meteo Weather & Tide Fetcher
Run this on your local machine to test the API integration before deploying to Pi.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.weather_fetcher import WeatherFetcher
from src.config import WEATHER_LATITUDE, WEATHER_LONGITUDE


def test_weather_fetcher():
    """Test the weather fetcher with current configuration"""
    print("=" * 60)
    print("Testing Open-Meteo Weather & Tide Fetcher")
    print("=" * 60)
    print(f"Location: {WEATHER_LATITUDE}, {WEATHER_LONGITUDE}")
    print()
    
    fetcher = WeatherFetcher()
    
    # Test 1: Fetch weather data
    print("1. Fetching weather data...")
    weather_data = fetcher.fetch_weather_data()
    if weather_data:
        print("   [OK] Weather data fetched successfully")
        print(f"   Current precipitation: {weather_data.get('current', {}).get('precipitation_mm', 0)} mm")
        print(f"   Current temp max: {weather_data.get('current', {}).get('temperature_max_c', 0)} °C")
        print(f"   Current temp min: {weather_data.get('current', {}).get('temperature_min_c', 0)} °C")
        print(f"   Daily forecast entries: {len(weather_data.get('daily', []))}")
        for i, day in enumerate(weather_data.get('daily', [])[:3]):
            print(f"     Day {i+1}: {day['date']} - Precip: {day['precipitation_mm']}mm, "
                  f"Tmax: {day['temperature_max_c']}°C, Tmin: {day['temperature_min_c']}°C")
    else:
        print("   [FAIL] Failed to fetch weather data")
        return False
    
    # Test 2: Fetch tide data
    print("\n2. Fetching tide data...")
    tide_data = fetcher.fetch_tide_data()
    if tide_data:
        print("   [OK] Tide data fetched successfully")
        print(f"   Current tide max: {tide_data.get('current', {}).get('tide_max_m', 0)} m")
        print(f"   Current tide min: {tide_data.get('current', {}).get('tide_min_m', 0)} m")
        print(f"   Daily forecast entries: {len(tide_data.get('daily', []))}")
        for i, day in enumerate(tide_data.get('daily', [])[:3]):
            print(f"     Day {i+1}: {day['date']} - Tide max: {day['tide_max_m']}m, "
                  f"Tide min: {day['tide_min_m']}m")
    else:
        print("   [FAIL] Failed to fetch tide data")
        return False
    
    # Test 3: Fetch combined data
    print("\n3. Fetching combined weather + tide data...")
    combined = fetcher.fetch_all_data()
    if combined:
        print("   [OK] Combined data fetched successfully")
        if 'tide' in combined:
            print("   Tide data included in combined response")
    else:
        print("   [FAIL] Failed to fetch combined data")
        return False
    
    # Test 4: Get weather for model
    print("\n4. Getting weather data formatted for model...")
    model_data = fetcher.get_weather_for_model()
    if model_data:
        print("   [OK] Model data prepared successfully")
        print(f"   R1 (1-day precip): {model_data.get('R1', 0)} mm")
        print(f"   R3 (3-day precip): {model_data.get('R3', 0)} mm")
        print(f"   R7 (7-day precip): {model_data.get('R7', 0)} mm")
        print(f"   Rainy days (7d): {model_data.get('rainy_days', 0)}")
        print(f"   TMAX: {model_data.get('TMAX', 0)} °C")
        print(f"   TMIN: {model_data.get('TMIN', 0)} °C")
        print(f"   TideMax: {model_data.get('TideMax', 0)} m")
        print(f"   TideMin: {model_data.get('TideMin', 0)} m")
    else:
        print("   [FAIL] Failed to prepare model data")
        return False
    
    # Test 5: Get current tide level
    print("\n5. Getting current tide level...")
    tide_level = fetcher.get_current_tide_level()
    if tide_level is not None:
        print(f"   [OK] Current tide level: {tide_level:.2f} m")
    else:
        print("   [WARN] Could not determine current tide level (using cached data)")
    
    # Test 6: Get forecast rain 24h
    print("\n6. Getting 24-hour forecast rain...")
    forecast_rain = fetcher.get_forecast_rain_24h()
    print(f"   Forecast rain (24h): {forecast_rain:.1f} mm")
    
    # Test 7: Test caching
    print("\n7. Testing cache...")
    fetcher.cache_weather_data(combined)
    cached = fetcher.get_cached_weather()
    if cached:
        print("   [OK] Cache write/read successful")
    else:
        print("   [FAIL] Cache failed")
        return False
    
    print("\n" + "=" * 60)
    print("All tests passed! [OK]")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_weather_fetcher()
    sys.exit(0 if success else 1)