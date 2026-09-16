"""
Prediction Module for River Monitor AI System
Handles real-time predictions using the trained Random Forest model + Fuzzy Logic
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import joblib

from src.config import (
    MODEL_PATH, CRITICAL_LEVEL_M, RISK_THRESHOLDS,
    FORECAST_DAYS, RECEDING_HOURS, ROR_WINDOW_MINUTES,
    RF_CLASSES
)
from src.data.database import (
    get_latest_water_level, get_water_levels_since,
    get_latest_prediction, insert_prediction,
    get_rainfall_24h_total
)
from src.data.weather_fetcher import WeatherFetcher
from src.model.preprocess import load_scaler, preprocess_for_prediction_new
from src.model.fuzzy_logic import compute_flood_risk, get_fuzzy_system


def _to_native(obj):
    """Recursively convert numpy scalars to native Python types for JSON serialization."""
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_native(v) for v in obj]
    return obj


class FloodPredictor:
    """Handles flood risk predictions using the trained model + fuzzy logic"""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.weather_fetcher = WeatherFetcher()
        self.fuzzy_system = get_fuzzy_system()
        self.load_model()
    
    def load_model(self) -> bool:
        """Load the trained model and scaler"""
        try:
            # Load model
            if os.path.exists(MODEL_PATH):
                self.model = joblib.load(MODEL_PATH)
                print(f"Model loaded from {MODEL_PATH}")
            else:
                print(f"Model file not found: {MODEL_PATH}")
                return False
            
            # Load scaler
            scaler_path = os.path.join(os.path.dirname(MODEL_PATH), "scaler.pkl")
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
                print(f"Scaler loaded from {scaler_path}")
            else:
                print(f"Scaler file not found: {scaler_path}")
                return False
            
            return True
            
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def get_current_features(self) -> Optional[Dict]:
        """Get current features for prediction"""
        # Get latest water level
        latest_water = get_latest_water_level()
        if not latest_water:
            print("No water level data available")
            return None
        
        # Get weather data (includes RF features)
        weather_data = self.weather_fetcher.get_weather_for_model()
        if not weather_data:
            print("No weather data available")
            return None
        
        # Get historical water levels for RoR computation (last 5 minutes)
        historical_levels = get_water_levels_since(hours=1)  # Last hour for 5-min window
        
        # Compute Rate of Rise (RoR) from last 5 minutes of 1-min data
        rate_of_rise_mm_day = 0.0
        if len(historical_levels) >= 2:
            # Get last 5 minutes of data
            recent_5min = historical_levels[-5:] if len(historical_levels) >= 5 else historical_levels
            if len(recent_5min) >= 2:
                # Water level in meters, convert to mm
                current_level_mm = latest_water['water_level_m'] * 1000
                prev_level_mm = recent_5min[0]['water_level_m'] * 1000
                time_diff_minutes = len(recent_5min) - 1  # Approximate minutes
                
                if time_diff_minutes > 0:
                    # Rate of rise in mm per minute, convert to mm/day
                    rate_mm_per_min = (current_level_mm - prev_level_mm) / time_diff_minutes
                    rate_of_rise_mm_day = rate_mm_per_min * 1440  # 1440 minutes in a day
        
        # Get current tide level
        tide_level_m = self.weather_fetcher.get_current_tide_level()
        if tide_level_m is None:
            tide_level_m = 0.0
        
        # Get forecast rain for next 24 hours
        forecast_rain_mm = self.weather_fetcher.get_forecast_rain_24h()
        
        # Build feature dictionary for RF model
        rf_features = {
            'R1': weather_data.get('R1', 0),
            'R3': weather_data.get('R3', 0),
            'R7': weather_data.get('R7', 0),
            'rainy_days': weather_data.get('rainy_days', 0),
            'TMAX': weather_data.get('TMAX', 0),
            'TMIN': weather_data.get('TMIN', 0),
            'TideMax': weather_data.get('TideMax', 0),
            'TideMin': weather_data.get('TideMin', 0),
            'timestamp': datetime.now()
        }
        
        # Also include data for fuzzy logic
        rf_features.update({
            'water_level_mm': latest_water['water_level_m'] * 1000,
            'rate_of_rise_mm_day': rate_of_rise_mm_day,
            'forecast_rain_mm': forecast_rain_mm,
            'tide_level_m': tide_level_m
        })
        
        return rf_features
    
    def predict_rf_propensity(self, features: Dict) -> Tuple[int, str]:
        """Predict flood propensity using Random Forest model"""
        if not self.model or not self.scaler:
            raise RuntimeError("Model or scaler not loaded")
        
        # Preprocess features for RF model
        X_scaled = preprocess_for_prediction_new(features, self.scaler)
        
        # Predict
        prediction = self.model.predict(X_scaled)[0]
        
        # Map to class name
        propensity_class = RF_CLASSES.get(prediction, 'Unknown')
        
        return prediction, propensity_class
    
    def predict_fuzzy_risk(self, features: Dict, rf_propensity: int) -> Dict:
        """Predict flood risk using fuzzy logic"""
        # Extract fuzzy inputs
        water_level_mm = features.get('water_level_mm', 0)
        rate_of_rise_mm_day = features.get('rate_of_rise_mm_day', 0)
        forecast_rain_mm = features.get('forecast_rain_mm', 0)
        tide_level_m = features.get('tide_level_m', 0)
        
        # Compute fuzzy risk
        fuzzy_result = compute_flood_risk(
            water_level_mm=water_level_mm,
            rate_of_rise_mm_day=rate_of_rise_mm_day,
            forecast_rain_mm=forecast_rain_mm,
            tide_level_m=tide_level_m,
            rf_propensity=rf_propensity
        )
        
        return fuzzy_result
    
    def predict_forecast(self, features: Dict, days: int = FORECAST_DAYS) -> List[float]:
        """
        Predict water level forecast for the next N days
        
        Note: This is a simplified approach. For better results, consider:
        1. Using a time series model (LSTM, ARIMA) for the forecast
        2. Using the Random Forest to predict changes rather than absolute values
        
        For now, we'll use a simple linear extrapolation based on recent trends.
        """
        # Get current water level
        current_level = features.get('water_level_mm', 0) / 1000.0  # Convert to meters
        
        # Get trend from recent changes (1-day change)
        # We'll use the rate of rise to estimate daily change
        rate_of_rise_mm_day = features.get('rate_of_rise_mm_day', 0)
        daily_change = rate_of_rise_mm_day / 1000.0  # Convert to meters/day
        
        # Generate forecast
        forecast = []
        for day in range(days):
            predicted_level = current_level + (daily_change * day)
            # Ensure forecast doesn't go negative
            predicted_level = max(0, predicted_level)
            forecast.append(round(predicted_level, 3))
        
        return forecast
    
    def make_prediction(self) -> Optional[Dict]:
        """
        Make a complete prediction (RF propensity + fuzzy risk + forecast)
        
        Returns:
            Dictionary with prediction results or None if failed
        """
        # Get current features
        features = self.get_current_features()
        if not features:
            return None
        
        # Predict RF propensity
        rf_propensity_num, rf_propensity_class = self.predict_rf_propensity(features)
        
        # Predict fuzzy risk
        fuzzy_result = self.predict_fuzzy_risk(features, rf_propensity_num)
        risk_level = fuzzy_result['risk_level']
        
        # Generate forecast
        forecast = self.predict_forecast(features, FORECAST_DAYS)
        
        # Calculate forecast change (change in next day)
        current_level = features.get('water_level_mm', 0) / 1000.0
        if len(forecast) >= 1:
            forecast_change = forecast[0] - current_level  # Change in 1 day
        else:
            forecast_change = 0
        
# Store prediction in database
        insert_prediction(
            timestamp=datetime.now(),
            current_level_m=current_level,
            risk_level=risk_level,
            rf_propensity=rf_propensity_class,
            fuzzy_inputs=_to_native(fuzzy_result.get('inputs', {})),
            rule_triggered=fuzzy_result.get('rule_triggered'),
            forecast_data=forecast,
            model_version="2.0"
        )

        # Return prediction results
        return _to_native({
            'timestamp': datetime.now().isoformat(),
            'current_level_m': current_level,
            'risk_level': risk_level,
            'rf_propensity': rf_propensity_class,
            'rf_propensity_num': rf_propensity_num,
            'fuzzy_result': fuzzy_result,
            'forecast': forecast,
            'forecast_change_1d': forecast_change,
            'features': features
        })
    
    def get_latest_prediction(self) -> Optional[Dict]:
        """Get the latest prediction from database"""
        prediction = get_latest_prediction()
        if prediction:
            # Convert forecast_data from JSON string to list
            if isinstance(prediction['forecast_data'], str):
                prediction['forecast_data'] = json.loads(prediction['forecast_data'])
            if isinstance(prediction['fuzzy_inputs'], str):
                prediction['fuzzy_inputs'] = json.loads(prediction['fuzzy_inputs'])
            return prediction
        return None


def get_current_prediction() -> Optional[Dict]:
    """Get current prediction (convenience function)"""
    predictor = FloodPredictor()
    return predictor.make_prediction()


def predict_and_alert():
    """Make prediction and send SMS alerts if needed"""
    from src.data.sms_handler import send_alert_sms
    
    predictor = FloodPredictor()
    prediction = predictor.make_prediction()
    
    if prediction and prediction['risk_level'] in ['alarm', 'critical']:
        # Send SMS alert
        send_alert_sms(
            prediction['risk_level'],
            prediction['current_level_m'],
            prediction['forecast_change_1d']
        )
    
    return prediction


if __name__ == "__main__":
    # Test prediction
    print("Testing Flood Predictor...")
    
    predictor = FloodPredictor()
    
    if not predictor.model or not predictor.scaler:
        print("Error: Model or scaler not loaded. Run train.py first.")
    else:
        # Make a test prediction
        prediction = predictor.make_prediction()
        
        if prediction:
            print(f"\nCurrent Prediction:")
            print(f"  Timestamp: {prediction['timestamp']}")
            print(f"  Current Water Level: {prediction['current_level_m']:.2f}m")
            print(f"  Risk Level: {prediction['risk_level']}")
            print(f"  RF Propensity: {prediction['rf_propensity']}")
            print(f"  Fuzzy Crisp Output: {prediction['fuzzy_result'].get('risk_crisp', 'N/A')}")
            print(f"  Rule Triggered: {prediction['fuzzy_result'].get('rule_triggered', 'N/A')}")
            print(f"  Forecast Change (1d): {prediction['forecast_change_1d']:+.3f}m")
            print(f"  Forecast (next 7d): {prediction['forecast']}")
        else:
            print("Failed to make prediction (missing data)")