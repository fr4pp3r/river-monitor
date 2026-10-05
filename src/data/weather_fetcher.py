"""
Weather & Tide Data Fetcher for River Monitor System
Downloads weather and tide data from Open-Meteo APIs
"""

import requests
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional, List

# Ensure the project root is on the module search path so that
# "from src.config import ..." styles of absolute imports work
# regardless of the directory this script is invoked from.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src import config as cfg
from src.data.database import (
    insert_weather_data, get_latest_weather,
    insert_tidal_data, clear_tidal_data_since, get_tide_level_at,
    get_rainfall_daily_range
)


class WeatherFetcher:
    """Fetches weather and tide data from Open-Meteo APIs"""
    
    def __init__(self):
        self.cache_dir = "data/weather_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def fetch_weather_data(self) -> Optional[Dict]:
        """Fetch weather forecast from Open-Meteo API"""
        params = {
            'latitude': cfg.WEATHER_LATITUDE,
            'longitude': cfg.WEATHER_LONGITUDE,
            'daily': cfg.WEATHER_DAILY_PARAMS,
            'hourly': cfg.WEATHER_HOURLY_PARAMS,
            'timezone': cfg.WEATHER_TIMEZONE,
            'forecast_days': cfg.WEATHER_FORECAST_DAYS
        }
        
        try:
            response = requests.get(cfg.WEATHER_API_URL, params=params, timeout=10)
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
            'latitude': cfg.WEATHER_LATITUDE,
            'longitude': cfg.WEATHER_LONGITUDE,
            'hourly': cfg.MARINE_HOURLY_PARAMS,
            'timezone': cfg.WEATHER_TIMEZONE,
            'forecast_days': cfg.WEATHER_FORECAST_DAYS
        }
        
        try:
            response = requests.get(cfg.MARINE_API_URL, params=params, timeout=10)
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
        
        # Extract nearest current hourly values (temp / humidity / pressure)
        # so the dashboard's current-weather card has real data.
        if 'hourly' in api_data:
            hourly = api_data['hourly']
            times = hourly.get('time', [])
            temps = hourly.get('temperature_2m', [])
            humidities = hourly.get('relative_humidity_2m', [])
            pressures = hourly.get('surface_pressure', [])
            hourly_precip = hourly.get('precipitation', [])
            
            if times:
                # Find the hourly slot closest to now
                now = datetime.now().replace(minute=0, second=0, microsecond=0)
                closest_idx = None
                closest_diff = None
                for i, time_str in enumerate(times):
                    try:
                        slot = datetime.fromisoformat(time_str)
                    except ValueError:
                        continue
                    diff = abs((slot - now).total_seconds())
                    if closest_diff is None or diff < closest_diff:
                        closest_diff = diff
                        closest_idx = i
                
                if closest_idx is not None:
                    processed['current'].update({
                        'temperature_c': temps[closest_idx] if closest_idx < len(temps) else None,
                        'humidity_percent': humidities[closest_idx] if closest_idx < len(humidities) else None,
                        'pressure_hpa': pressures[closest_idx] if closest_idx < len(pressures) else None,
                        'hourly_precipitation_mm': hourly_precip[closest_idx] if closest_idx < len(hourly_precip) else None
                    })
        
        return processed
    
    def process_tide_data(self, api_data: Dict) -> Dict:
        """Process raw tide API data (hourly) into daily max/min + hourly series"""
        processed = {
            'timestamp': datetime.now(),
            'daily': [],
            'hourly': []
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
                
                processed['hourly'].append({'timestamp': dt, 'tide_level_m': sea_level})
                
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
            if (datetime.now() - cache_time).total_seconds() < cfg.WEATHER_CACHE_EXPIRY:
                return cache_data['data']
            else:
                return None
                
        except (json.JSONDecodeError, ValueError):
            return None
    
    def store_weather_in_db(self, data: Optional[Dict] = None):
        """Fetch weather and tide data and store in database"""
        data = data or self.fetch_all_data()
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
                'pressure_hpa': current.get('pressure_hpa'),
                'temperature_c': current.get('temperature_c'),
                'humidity_percent': current.get('humidity_percent'),
                'forecast_data': json.dumps(serializable_daily),
                'tide_forecast_data': json.dumps(serializable_tide_daily)
            }
            
            insert_weather_data(datetime.now(), current_data)

            # Clear from today 00:00 onward so the fresh forecast replaces the
            # predictive window while preserving earlier stored tidal readings
            tide_hourly = data.get('tide', {}).get('hourly', [])
            if tide_hourly:
                try:
                    since = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    clear_tidal_data_since(since)
                    for pt in tide_hourly:
                        ts = pt.get('timestamp')
                        tl = pt.get('tide_level_m')
                        if ts is not None and tl is not None:
                            insert_tidal_data(ts, float(tl))
                except Exception as e:
                    print(f"Warning: failed to store hourly tide data: {e}")

            # Cache the data
            self.cache_weather_data(data)
            
            print("Weather and tide data stored in database")
            return True
        
        return False
    
    def get_weather_for_model(self, horizon: str = "24h") -> Dict:
        """Get weather data formatted for the prediction model.

        horizon selects the reference day: '24h' uses today, '48h' uses tomorrow.
        Precipitation features blend sensor rainfall (past days) with the saved
        forecast (today/tomorrow): R1 = reference-day total, R3 = 3-day total
        ending at reference day, R7 = 7-day total ending at reference day.
        """
        # Get latest weather from DB, rejecting an expired forecast so the
        # branch below refetches rather than predicting from a stale window
        latest_weather = get_latest_weather(max_age_seconds=cfg.WEATHER_STALE_AFTER)
        if not latest_weather:
            # Try to fetch fresh data
            if not self.store_weather_in_db():
                return {}
            latest_weather = get_latest_weather()

        # Get forecast data
        forecast_data = json.loads(latest_weather.get('forecast_data', '[]'))
        tide_forecast_data = json.loads(latest_weather.get('tide_forecast_data', '[]'))

        # Reference day index into the forecast arrays (0=today for 24h, 1=tomorrow for 48h)
        ref_idx = 0 if horizon == '24h' else 1

        # Sensor-measured daily rainfall for the trailing 7 calendar days
        today = datetime.now().date()
        start = today - timedelta(days=7)
        sensor_daily = {}
        try:
            rows = get_rainfall_daily_range(
                datetime.combine(start, datetime.min.time()),
                datetime.combine(today, datetime.min.time())
            )
            for row in rows:
                sensor_daily[row['date']] = row.get('total_rainfall_mm', 0) or 0
        except Exception as e:
            print(f"Warning: failed to read sensor daily rainfall: {e}")
            sensor_daily = {}

        def day_rain(offset: int) -> float:
            """Rainfall for the day at `offset` from today (negative = past day)"""
            day_str = (today + timedelta(days=offset)).isoformat()
            if offset < 0:
                return sensor_daily.get(day_str, 0.0)
            if offset < len(forecast_data):
                forecast_mm = forecast_data[offset].get('precipitation_mm', 0) or 0
                if forecast_mm:
                    return forecast_mm
            return sensor_daily.get(day_str, 0.0)

        R1 = day_rain(ref_idx)
        R3 = day_rain(ref_idx - 2) + day_rain(ref_idx - 1) + day_rain(ref_idx)
        R7 = sum(day_rain(i) for i in range(ref_idx - 6, ref_idx + 1))

        # Consecutive rainy days ending at the reference day (rainfall > 2mm)
        rain_days = 0
        offset = ref_idx
        while offset >= ref_idx - 10:
            if day_rain(offset) <= cfg.RAIN_DAY_THRESHOLD_MM:
                break
            rain_days += 1
            offset -= 1

        if ref_idx < len(forecast_data):
            TMAX = forecast_data[ref_idx].get('temperature_max_c')
            TMIN = forecast_data[ref_idx].get('temperature_min_c')
        else:
            TMAX = latest_weather.get('temperature_max_c')
            TMIN = latest_weather.get('temperature_min_c')

        if ref_idx < len(tide_forecast_data):
            TideMax = tide_forecast_data[ref_idx].get('tide_max_m')
            TideMin = tide_forecast_data[ref_idx].get('tide_min_m')
        else:
            TideMax = latest_weather.get('tide_max_m')
            TideMin = latest_weather.get('tide_min_m')

        # Fuzzy FRain = reference-day precipitation; fuzzy Tide = the tide at the
        # reference day's same clock hour from the stored hourly series
        tide_target = datetime.now() + (timedelta(hours=24) if horizon == '48h' else timedelta(hours=0))
        tide_row = get_tide_level_at(tide_target)
        tide_level_m = float(tide_row.get('tide_level_m')) if tide_row and tide_row.get('tide_level_m') is not None else None
        if tide_level_m is None:
            tide_level_m = self.get_current_tide_level() or 0.0

        return {
            'R1': R1,
            'R3': R3,
            'R7': R7,
            'rain_days': rain_days,
            'TMAX': TMAX or 0,
            'TMIN': TMIN or 0,
            'TideMax': TideMax or 0,
            'TideMin': TideMin or 0,
            'precipitation_mm': day_rain(ref_idx),
            'forecast_rain_mm': day_rain(ref_idx),
            'tide_level_m': tide_level_m,
            'temperature_max_c': TMAX or 0,
            'temperature_min_c': TMIN or 0,
            'tide_max_m': TideMax or 0,
            'tide_min_m': TideMin or 0,
            'horizon': horizon
        }

    def get_current_tide_level(self) -> Optional[float]:
        """Get the current tide level from the stored hourly tidal data"""
        row = get_tide_level_at(datetime.now())
        if row is not None and row.get('tide_level_m') is not None:
            return float(row['tide_level_m'])

        # Fallback: cached daily max/min estimate
        cached = self.get_cached_weather()
        if cached and 'tide' in cached:
            tide_current = cached['tide'].get('current', {})
            tide_max = tide_current.get('tide_max_m')
            tide_min = tide_current.get('tide_min_m')
            if tide_max is not None and tide_min is not None:
                return (tide_max + tide_min) / 2
            elif tide_max is not None:
                return tide_max
        return None


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
        fetcher.store_weather_in_db(data)
    else:
        print("Failed to fetch weather data")