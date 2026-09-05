"""
Weather & Tide Data Fetcher for River Monitor System
Downloads weather and tide data from Open-Meteo APIs
"""

import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List

from src.config import (
    WEATHER_API_URL, MARINE_API_URL,
    WEATHER_LATITUDE, WEATHER_LONGITUDE,
    WEATHER_DAILY_PARAMS, MARINE_HOURLY_PARAMS,
    WEATHER_TIMEZONE, WEATHER_FORECAST_DAYS,
    WEATHER_CACHE_EXPIRY
)
from src.data.database import insert_weather_data, get_latest_weather


class WeatherFetcher:
    """Fetches weather and tide data from Open-Meteo APIs"""
    
    def __init__(self):
        self.cache_dir = "data/weather_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def fetch_weather_data(self) -> Optional[Dict]:
        """Fetch weather forecast from Open-Meteo API"""
        params = {
            'latitude': WEATHER_LATITUDE,
            'longitude': WEATHER_LONGITUDE,
            'daily': WEATHER_DAILY_PARAMS,
            'timezone': WEATHER_TIMEZONE,
            'forecast_days': WEATHER_FORECAST_DAYS
        }
        
        try:
            response = requests.get(WEATHER_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Process and return data
            return self.process_weather_data(data)
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching weather data: {e}")
            return None
    
    def fetch_tide_data(self) -> Optional[Dict]:
        """Fetch tide forecast from Open-Meteo Marine API (hourly sea level, derive daily max/min)"""
        params = {
            'latitude': WEATHER_LATITUDE,
            'longitude': WEATHER_LONGITUDE,
            'hourly': MARINE_HOURLY_PARAMS,
            'timezone': WEATHER_TIMEZONE,
            'forecast_days': WEATHER_FORECAST_DAYS
        }
        
        try:
            response = requests.get(MARINE_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Process and return data
            return self.process_tide_data(data)
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching tide data: {e}")
            return None
    
    def fetch_all_data(self) -> Optional[Dict]:
        """Fetch both weather and tide data"""
        weather_data = self.fetch_weather_data()
        tide_data = self.fetch_tide_data()
        
        if weather_data and tide_data:
            # Merge tide data into weather data
            weather_data['tide'] = tide_data
            return weather_data
        elif weather_data:
            print("Warning: Weather data fetched but tide data failed")
            return weather_data
        elif tide_data:
            print("Warning: Tide data fetched but weather data failed")
            return {'tide': tide_data}
        
        return None
    
    def process_weather_data(self, api_data: Dict) -> Dict:
        """Process raw weather API data into structured format"""
        processed = {
            'timestamp': datetime.now(),
            'current': {},
            'daily': []
        }
        
        # Process daily forecast
        if 'daily' in api_data:
            daily = api_data['daily']
            dates = daily.get('time', [])
            temp_max = daily.get('temperature_2m_max', [])
            temp_min = daily.get('temperature_2m_min', [])
            precip = daily.get('precipitation_sum', [])
            
            for i, date_str in enumerate(dates):
                processed['daily'].append({
                    'date': date_str,
                    'timestamp': datetime.fromisoformat(date_str),
                    'temperature_max_c': temp_max[i] if i < len(temp_max) else None,
                    'temperature_min_c': temp_min[i] if i < len(temp_min) else None,
                    'precipitation_mm': precip[i] if i < len(precip) else 0.0
                })
            
            # Current values (first day)
            if processed['daily']:
                first = processed['daily'][0]
                processed['current'] = {
                    'temperature_max_c': first['temperature_max_c'],
                    'temperature_min_c': first['temperature_min_c'],
                    'precipitation_mm': first['precipitation_mm']
                }
        
        return processed
    
    def process_tide_data(self, api_data: Dict) -> Dict:
        """Process raw tide API data (hourly) into daily max/min format"""
        processed = {
            'timestamp': datetime.now(),
            'daily': []
        }
        
        if 'hourly' in api_data:
            hourly = api_data['hourly']
            times = hourly.get('time', [])
            sea_levels = hourly.get('sea_level_height_msl', [])
            
            # Group hourly data by date and compute daily max/min
            daily_data = {}
            for i, time_str in enumerate(times):
                if i >= len(sea_levels):
                    break
                sea_level = sea_levels[i]
                if sea_level is None:
                    continue
                    
                # Parse date from ISO timestamp (e.g., "2026-09-05T00:00")
                try:
                    dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                    date_key = dt.date().isoformat()
                except ValueError:
                    continue
                
                if date_key not in daily_data:
                    daily_data[date_key] = {'max': sea_level, 'min': sea_level}
                else:
                    daily_data[date_key]['max'] = max(daily_data[date_key]['max'], sea_level)
                    daily_data[date_key]['min'] = min(daily_data[date_key]['min'], sea_level)
            
            # Convert to daily list sorted by date
            for date_key in sorted(daily_data.keys()):
                day_data = daily_data[date_key]
                processed['daily'].append({
                    'date': date_key,
                    'timestamp': datetime.fromisoformat(date_key),
                    'tide_max_m': day_data['max'],
                    'tide_min_m': day_data['min']
                })
            
            # Current values (first day)
            if processed['daily']:
                first = processed['daily'][0]
                processed['current'] = {
                    'tide_max_m': first['tide_max_m'],
                    'tide_min_m': first['tide_min_m']
                }
        
        return processed
    
    def cache_weather_data(self, data: Dict):
        """Cache weather and tide data to file"""
        cache_file = os.path.join(self.cache_dir, "weather_cache.json")
        
        def convert_datetime(obj):
            """Recursively convert datetime objects to ISO format strings"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(item) for item in obj]
            else:
                return obj
        
        serializable_data = convert_datetime(data)
        
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'data': serializable_data
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
    
    def get_cached_weather(self) -> Optional[Dict]:
        """Get cached weather data if still valid"""
        cache_file = os.path.join(self.cache_dir, "weather_cache.json")
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Check if cache is still valid
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            if (datetime.now() - cache_time).total_seconds() < WEATHER_CACHE_EXPIRY:
                return cache_data['data']
            else:
                return None
                
        except (json.JSONDecodeError, ValueError):
            return None
    
    def store_weather_in_db(self):
        """Fetch weather and tide data and store in database"""
        data = self.fetch_all_data()
        if data:
            # Prepare current weather data
            current = data.get('current', {})
            tide_current = data.get('tide', {}).get('current', {})
            
            # Convert daily data to JSON-serializable format
            daily_data = data.get('daily', [])
            serializable_daily = []
            for day in daily_data:
                day_copy = day.copy()
                if 'timestamp' in day_copy and hasattr(day_copy['timestamp'], 'isoformat'):
                    day_copy['timestamp'] = day_copy['timestamp'].isoformat()
                serializable_daily.append(day_copy)
            
            tide_daily = data.get('tide', {}).get('daily', [])
            serializable_tide_daily = []
            for day in tide_daily:
                day_copy = day.copy()
                if 'timestamp' in day_copy and hasattr(day_copy['timestamp'], 'isoformat'):
                    day_copy['timestamp'] = day_copy['timestamp'].isoformat()
                serializable_tide_daily.append(day_copy)
            
            current_data = {
                'precipitation_mm': current.get('precipitation_mm', 0),
                'temperature_max_c': current.get('temperature_max_c'),
                'temperature_min_c': current.get('temperature_min_c'),
                'tide_max_m': tide_current.get('tide_max_m'),
                'tide_min_m': tide_current.get('tide_min_m'),
                'forecast_data': json.dumps(serializable_daily),
                'tide_forecast_data': json.dumps(serializable_tide_daily)
            }
            
            insert_weather_data(datetime.now(), current_data)
            
            # Cache the data
            self.cache_weather_data(data)
            
            print("Weather and tide data stored in database")
            return True
        
        return False
    
    def get_weather_for_model(self) -> Dict:
        """Get weather data formatted for the prediction model"""
        # Get latest weather from DB
        latest_weather = get_latest_weather()
        if not latest_weather:
            # Try to fetch fresh data
            if not self.store_weather_in_db():
                return {}
            latest_weather = get_latest_weather()
        
        # Get forecast data
        forecast_data = json.loads(latest_weather.get('forecast_data', '[]'))
        tide_forecast_data = json.loads(latest_weather.get('tide_forecast_data', '[]'))
        
        # Calculate aggregated values for daily model
        R1 = 0
        R3 = 0
        R7 = 0
        rainy_days = 0
        TMAX = latest_weather.get('temperature_max_c', 0)
        TMIN = latest_weather.get('temperature_min_c', 0)
        TideMax = latest_weather.get('tide_max_m', 0)
        TideMin = latest_weather.get('tide_min_m', 0)
        
        if forecast_data:
            # R1: Today's precipitation
            R1 = forecast_data[0].get('precipitation_mm', 0) if forecast_data else 0
            
            # R3: 3-day precipitation sum
            for day in forecast_data[:3]:
                R3 += day.get('precipitation_mm', 0)
            
            # R7: 7-day precipitation sum
            for day in forecast_data[:7]:
                R7 += day.get('precipitation_mm', 0)
            
            # Rainy days in next 7 days
            for day in forecast_data[:7]:
                if day.get('precipitation_mm', 0) > 0:
                    rainy_days += 1
        
        if tide_forecast_data:
            # TideMax: Maximum tide in next 7 days
            tide_maxes = [day.get('tide_max_m', 0) for day in tide_forecast_data[:7] if day.get('tide_max_m') is not None]
            if tide_maxes:
                TideMax = max(tide_maxes)
            
            # TideMin: Minimum tide in next 7 days
            tide_mins = [day.get('tide_min_m', 0) for day in tide_forecast_data[:7] if day.get('tide_min_m') is not None]
            if tide_mins:
                TideMin = min(tide_mins)
        
        return {
            'R1': R1,
            'R3': R3,
            'R7': R7,
            'rainy_days': rainy_days,
            'TMAX': TMAX,
            'TMIN': TMIN,
            'TideMax': TideMax,
            'TideMin': TideMin,
            'precipitation_mm': latest_weather.get('precipitation_mm', 0),
            'temperature_max_c': latest_weather.get('temperature_max_c', 0),
            'temperature_min_c': latest_weather.get('temperature_min_c', 0),
            'tide_max_m': latest_weather.get('tide_max_m', 0),
            'tide_min_m': latest_weather.get('tide_min_m', 0)
        }
    
    def get_current_tide_level(self) -> Optional[float]:
        """Get current tide level from cached data"""
        cached = self.get_cached_weather()
        if cached and 'tide' in cached:
            tide_current = cached['tide'].get('current', {})
            # Return average of max and min as current estimate
            tide_max = tide_current.get('tide_max_m')
            tide_min = tide_current.get('tide_min_m')
            if tide_max is not None and tide_min is not None:
                return (tide_max + tide_min) / 2
            elif tide_max is not None:
                return tide_max
        return None
    
    def get_forecast_rain_24h(self) -> float:
        """Get forecasted precipitation for next 24 hours"""
        cached = self.get_cached_weather()
        if cached and 'daily' in cached:
            return cached['daily'][0].get('precipitation_mm', 0) if cached['daily'] else 0
        return 0.0


def fetch_and_store_weather():
    """Fetch weather and tide data and store in database (for cron job)"""
    fetcher = WeatherFetcher()
    fetcher.store_weather_in_db()


if __name__ == "__main__":
    # Test weather fetching
    fetcher = WeatherFetcher()
    data = fetcher.fetch_all_data()
    if data:
        print("Current weather:")
        print(f"  Precipitation: {data.get('current', {}).get('precipitation_mm', 0)} mm")
        print(f"  Temp Max: {data.get('current', {}).get('temperature_max_c', 0)} °C")
        print(f"  Temp Min: {data.get('current', {}).get('temperature_min_c', 0)} °C")
        
        if 'tide' in data:
            print(f"  Tide Max: {data['tide'].get('current', {}).get('tide_max_m', 0)} m")
            print(f"  Tide Min: {data['tide'].get('current', {}).get('tide_min_m', 0)} m")
        
        print("\n7-day forecast:")
        for day in data.get('daily', [])[:3]:
            print(f"  {day['date']}: Precip={day['precipitation_mm']}mm, "
                  f"Tmax={day['temperature_max_c']}°C, Tmin={day['temperature_min_c']}°C")
        
        # Store in database
        fetcher.store_weather_in_db()
    else:
        print("Failed to fetch weather data")