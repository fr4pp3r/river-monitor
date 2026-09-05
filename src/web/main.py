"""
FastAPI Web Dashboard for River Monitor System
Provides a LAN-accessible dashboard for visualizing water levels, weather, and predictions
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from src.config import (
    DASHBOARD_HOST, DASHBOARD_PORT,
    AUTO_REFRESH_SECONDS, CRITICAL_LEVEL_M,
    RISK_THRESHOLDS, RISK_LEVELS
)
from src.data.database import (
    get_latest_water_level, get_water_levels_since,
    get_latest_weather, get_weather_since,
    get_latest_prediction, get_predictions_since,
    get_recent_alerts, get_system_status, get_database_stats,
    get_rainfall_since, get_rainfall_stats
)
from src.model.predict import FloodPredictor
from src.model.fuzzy_logic import get_fuzzy_system


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
                "status": "ok" if latest_water and latest_water['source'] == 'lora' else "warning",
                "last_update": latest_water['timestamp'] if latest_water else None,
                "message": "Receiving data" if latest_water and latest_water['source'] == 'lora' else "No recent LoRa data"
            },
            "sms": {
                "status": "ok" if latest_water and latest_water['source'] == 'sms' else "ok",
                "last_update": latest_water['timestamp'] if latest_water and latest_water['source'] == 'sms' else None,
                "message": "Fallback available"
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
            # Make a new prediction
            predictor = FloodPredictor()
            prediction = predictor.make_prediction()
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
    try:
        from src.data.sms_handler import send_alert_sms
        
        # Send a test alert
        send_alert_sms("test", 1.0, 0.0)
        
        return JSONResponse(content={"status": "success", "message": "Test alert sent"})
        
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


# ============================================================================
# MAIN
# ============================================================================

def run_dashboard():
    """Run the FastAPI dashboard server"""
    print(f"Starting River Monitor Dashboard on {DASHBOARD_HOST}:{DASHBOARD_PORT}")
    print(f"Access the dashboard at: http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
    
    uvicorn.run(
        app,
        host=DASHBOARD_HOST,
        port=DASHBOARD_PORT,
        reload=False  # Disable reload in production
    )


if __name__ == "__main__":
    run_dashboard()