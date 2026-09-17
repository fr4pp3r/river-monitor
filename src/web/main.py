"""
FastAPI Web Dashboard for River Monitor System
Provides a LAN-accessible dashboard for visualizing water levels, weather, and predictions
"""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

# Ensure the project root is on the module search path so that
# "from src.config import ..." styles of absolute imports work
# regardless of the directory this script is invoked from.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import src.config as config_module
from src.config import (
    DASHBOARD_HOST, DASHBOARD_PORT,
    AUTO_REFRESH_SECONDS, CRITICAL_LEVEL_M,
    RISK_THRESHOLDS, RISK_LEVELS,
    LORA_ENABLED, SMS_ENABLED
)
from src.config_manager import get_config_dict, apply_config_dict, reset_to_defaults
from src.data.database import (
    get_latest_water_level, get_water_levels_since,
    get_latest_weather, get_weather_since,
    get_latest_prediction, get_predictions_since,
    get_recent_alerts, get_system_status, get_database_stats,
    get_rainfall_since, get_rainfall_stats,
    get_all_alert_contacts, get_alert_contact,
    insert_alert_contact, update_alert_contact, delete_alert_contact,
    get_active_alert_phone_numbers
)
from src.data.sms_handler import test_alert_sms
from src.data.lora_receiver import start_lora_receiver_async
from src.model.predict import FloodPredictor
from src.data.weather_fetcher import WeatherFetcher


# Initialize FastAPI app
app = FastAPI(title="River Monitor Dashboard")

# Mount static files
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="src/web/templates")


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "auto_refresh_seconds": AUTO_REFRESH_SECONDS
    })


@app.get("/api/status")
async def get_status() -> JSONResponse:
    """Get system status"""
    try:
        # Get latest data timestamps
        latest_water = get_latest_water_level()
        latest_weather = get_latest_weather()
        latest_prediction = get_latest_prediction()
        
        # Get system component status
        system_status = get_system_status()
        
        # Build status response
        status = {
            "lora": {
                "enabled": LORA_ENABLED,
                "status": "disabled" if not LORA_ENABLED else ("ok" if latest_water and latest_water['source'] == 'lora' else "warning"),
                "last_update": latest_water['timestamp'] if latest_water else None,
                "message": "Module disabled" if not LORA_ENABLED else ("Receiving data" if latest_water and latest_water['source'] == 'lora' else "No recent LoRa data")
            },
            "sms": {
                "enabled": SMS_ENABLED,
                "status": "disabled" if not SMS_ENABLED else "ok",
                "last_update": latest_water['timestamp'] if latest_water and latest_water['source'] == 'sms' else None,
                "message": "Module disabled" if not SMS_ENABLED else "Fallback available"
            },
            "weather": {
                "status": "ok" if latest_weather else "warning",
                "last_update": latest_weather['timestamp'] if latest_weather else None,
                "message": "Data available" if latest_weather else "No weather data"
            },
            "model": {
                "status": "ok" if latest_prediction else "warning",
                "last_update": latest_prediction['timestamp'] if latest_prediction else None,
                "message": "Predictions available" if latest_prediction else "No predictions"
            },
            "database": get_database_stats(),
            "system_components": [dict(s) for s in system_status]
        }
        
        return JSONResponse(content=status)
        
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/water-levels")
async def get_water_levels(hours: int = 24) -> JSONResponse:
    """Get water level readings for the last N hours"""
    try:
        water_levels = get_water_levels_since(hours=hours)
        return JSONResponse(content=[dict(wl) for wl in water_levels])
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/weather")
async def get_weather(hours: int = 48) -> JSONResponse:
    """Get weather data for the last N hours"""
    try:
        weather_data = get_weather_since(hours=hours)
        
        # If the requested window is empty (e.g. stale/just-started DB), fall back
        # to the most recent weather reading so the dashboard can still display it.
        if not weather_data:
            latest = get_latest_weather()
            if latest:
                weather_data = [latest]
        
        return JSONResponse(content=[dict(w) for w in weather_data])
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/prediction")
async def get_prediction() -> JSONResponse:
    """Get the latest prediction"""
    try:
        # Try to get existing prediction first
        prediction = get_latest_prediction()
        
        if not prediction:
            # Try to make a new prediction from live data
            try:
                predictor = FloodPredictor()
                prediction = predictor.make_prediction()
            except Exception as pred_err:
                return JSONResponse(content={"error": str(pred_err)}, status_code=500)

            if prediction:
                # Convert to dict format
                prediction_dict = {
                    'timestamp': prediction['timestamp'],
                    'current_level_m': prediction['current_level_m'],
                    'risk_level': prediction['risk_level'],
                    'rf_propensity': prediction.get('rf_propensity', 'Unknown'),
                    'forecast': prediction['forecast'],
                    'forecast_change_1d': prediction['forecast_change_1d'],
                    'fuzzy_result': prediction.get('fuzzy_result', {})
                }
                return JSONResponse(content=prediction_dict)

            # No data available yet (e.g. no water level readings)
            return JSONResponse(content={"error": "No data available yet"}, status_code=409)

        # Format existing prediction
        if isinstance(prediction['forecast_data'], str):
            prediction['forecast_data'] = json.loads(prediction['forecast_data'])
        if isinstance(prediction['fuzzy_inputs'], str):
            prediction['fuzzy_inputs'] = json.loads(prediction['fuzzy_inputs'])
        
        return JSONResponse(content={
            'timestamp': prediction['timestamp'],
            'current_level_m': prediction['current_level_m'],
            'risk_level': prediction['risk_level'],
            'rf_propensity': prediction.get('rf_propensity', 'Unknown'),
            'forecast': prediction['forecast_data'],
            'forecast_change_1d': 0,  # Will be calculated in frontend
            'fuzzy_inputs': prediction.get('fuzzy_inputs', {}),
            'rule_triggered': prediction.get('rule_triggered')
        })
        
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/fuzzy-details")
async def get_fuzzy_details() -> JSONResponse:
    """Get detailed fuzzy logic information for the current prediction"""
    try:
        prediction = get_latest_prediction()
        if not prediction:
            return JSONResponse(content={"error": "No prediction available"}, status_code=404)
        
        # Get fuzzy inputs from prediction
        fuzzy_inputs = prediction.get('fuzzy_inputs', {})
        if isinstance(fuzzy_inputs, str):
            fuzzy_inputs = json.loads(fuzzy_inputs)
        
        # Get rule triggered
        rule_triggered = prediction.get('rule_triggered')
        
        # Get RF propensity
        rf_propensity = prediction.get('rf_propensity', 'Unknown')
        
        # Get current water level for display
        latest_water = get_latest_water_level()
        current_water_level_mm = latest_water['water_level_m'] * 1000 if latest_water else 0
        
        # Build detailed response
        details = {
            'timestamp': prediction['timestamp'],
            'risk_level': prediction['risk_level'],
            'rf_propensity': rf_propensity,
            'rule_triggered': rule_triggered,
            'current_water_level_mm': current_water_level_mm,
            'fuzzy_inputs': fuzzy_inputs,
            'risk_levels': RISK_LEVELS
        }
        
        return JSONResponse(content=details)
        
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/forecast")
async def get_forecast(days: int = 7) -> JSONResponse:
    """Get water level forecast for the next N days"""
    try:
        prediction = get_latest_prediction()
        if prediction:
            if isinstance(prediction['forecast_data'], str):
                forecast = json.loads(prediction['forecast_data'])
            else:
                forecast = prediction['forecast_data']
            
            # Return forecast with timestamps (daily)
            now = datetime.now()
            forecast_with_timestamps = [
                {
                    'timestamp': (now + timedelta(days=i)).isoformat(),
                    'water_level_m': level
                }
                for i, level in enumerate(forecast[:days])
            ]
            return JSONResponse(content=forecast_with_timestamps)
        
        return JSONResponse(content=[])
        
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/alerts")
async def get_alerts(limit: int = 50) -> JSONResponse:
    """Get recent alerts"""
    try:
        alerts = get_recent_alerts(limit=limit)
        return JSONResponse(content=[dict(a) for a in alerts])
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/rainfall")
async def get_rainfall(hours: int = 24) -> JSONResponse:
    """Get rainfall data for the last N hours"""
    try:
        rainfall_data = get_rainfall_since(hours=hours)
        return JSONResponse(content=[dict(r) for r in rainfall_data])
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/rainfall-stats")
async def get_rainfall_stats(hours: int = 24) -> JSONResponse:
    """Get rainfall statistics for the last N hours"""
    try:
        stats = get_rainfall_stats(hours=hours)
        return JSONResponse(content=stats)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# ============================================================================
# WEB HOOKS FOR MANUAL ACTIONS
# ============================================================================

@app.post("/api/refresh-prediction")
async def refresh_prediction() -> JSONResponse:
    """Manually trigger a new prediction"""
    try:
        predictor = FloodPredictor()
        prediction = predictor.make_prediction()
        
        if prediction:
            return JSONResponse(content={
                "status": "success",
                "prediction": prediction
            })
        else:
            return JSONResponse(content={"status": "error", "message": "Failed to make prediction"}, status_code=500)
            
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/test-alert")
async def test_alert() -> JSONResponse:
    """Test SMS alert system"""
    if not SMS_ENABLED:
        return JSONResponse(content={"status": "error", "message": "SMS module is disabled in config"}, status_code=400)
    
    try:
        from src.data.sms_handler import test_alert_sms
        
        # Send a test alert
        success = test_alert_sms()
        
        if success:
            return JSONResponse(content={"status": "success", "message": "Test alert sent"})
        else:
            return JSONResponse(content={"status": "error", "message": "Failed to send test alert"}, status_code=500)
        
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


# ============================================================================
# ALERT CONTACTS API ENDPOINTS
# ============================================================================

@app.get("/api/contacts")
async def get_contacts(active_only: bool = True) -> JSONResponse:
    """Get all alert contacts"""
    try:
        contacts = get_all_alert_contacts(active_only=active_only)
        return JSONResponse(content=contacts)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/contacts")
async def create_contact(request: Request) -> JSONResponse:
    """Create a new alert contact"""
    try:
        data = await request.json()
        name = data.get('name')
        phone_number = data.get('phone_number')
        receive_alert = data.get('receive_alert', 1)
        receive_warning = data.get('receive_warning', 1)
        receive_critical = data.get('receive_critical', 1)
        
        if not name or not phone_number:
            return JSONResponse(content={"error": "Name and phone number are required"}, status_code=400)
        
        contact_id = insert_alert_contact(
            name=name,
            phone_number=phone_number,
            receive_alert=receive_alert,
            receive_warning=receive_warning,
            receive_critical=receive_critical
        )
        
        return JSONResponse(content={"status": "success", "contact_id": contact_id})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.put("/api/contacts/{contact_id}")
async def update_contact(contact_id: int, request: Request) -> JSONResponse:
    """Update an alert contact"""
    try:
        data = await request.json()
        updates = {k: v for k, v in data.items() if k in ['name', 'phone_number', 'is_active', 'receive_alert', 'receive_warning', 'receive_critical']}
        
        if not updates:
            return JSONResponse(content={"error": "No valid fields to update"}, status_code=400)
        
        success = update_alert_contact(contact_id, **updates)
        
        if success:
            return JSONResponse(content={"status": "success"})
        else:
            return JSONResponse(content={"error": "Contact not found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.delete("/api/contacts/{contact_id}")
async def delete_contact(contact_id: int) -> JSONResponse:
    """Delete an alert contact"""
    try:
        success = delete_alert_contact(contact_id)
        
        if success:
            return JSONResponse(content={"status": "success"})
        else:
            return JSONResponse(content={"error": "Contact not found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/contacts/phone-numbers")
async def get_phone_numbers(risk_level: str = None) -> JSONResponse:
    """Get phone numbers for a specific risk level"""
    try:
        numbers = get_active_alert_phone_numbers(risk_level)
        return JSONResponse(content={"phone_numbers": numbers})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/contacts/{contact_id}")
async def get_contact(contact_id: int) -> JSONResponse:
    """Get a single alert contact by ID"""
    try:
        contact = get_alert_contact(contact_id)
        if contact:
            return JSONResponse(content=contact)
        else:
            return JSONResponse(content={"error": "Contact not found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# ============================================================================
# CONFIGURATION API ENDPOINTS
# ============================================================================

@app.get("/api/config")
async def get_config() -> JSONResponse:
    try:
        return JSONResponse(content=get_config_dict())
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.put("/api/config")
async def update_config(request: Request) -> JSONResponse:
    try:
        data = await request.json()
        ok, err = apply_config_dict(data)
        if ok:
            return JSONResponse(content={"status": "success"})
        return JSONResponse(content={"error": err}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/config/reset")
async def reset_config() -> JSONResponse:
    try:
        ok, err = reset_to_defaults()
        if ok:
            return JSONResponse(content={"status": "success"})
        return JSONResponse(content={"error": err}, status_code=500)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# ============================================================================
# MAIN
# ============================================================================

def run_dashboard():
    """Run the FastAPI dashboard server"""
    print(f"Starting River Monitor Dashboard on {DASHBOARD_HOST}:{DASHBOARD_PORT}")
    print(f"Access the dashboard at: http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
    
# Try to fetch and store fresh weather/tide data so the dashboard has
    # up-to-date readings even before the first sensor packet arrives.
    try:
        fetcher = WeatherFetcher()
        if fetcher.store_weather_in_db():
            print("Weather and tide data refreshed at startup")
        else:
            print("Warning: Could not refresh weather data at startup (using cached/last known)")
    except Exception as e:
        print(f"Warning: Weather refresh at startup failed: {e}")

    # Start the LoRa receiver loop in a background thread so sensor packets
    # are ingested and stored while the web dashboard keeps running.
    start_lora_receiver_async()

    uvicorn.run(
        app,
        host=DASHBOARD_HOST,
        port=DASHBOARD_PORT,
        reload=False  # Disable reload in production
    )


if __name__ == "__main__":
    run_dashboard()