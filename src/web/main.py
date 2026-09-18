"""
FastAPI Web Dashboard for River Monitor System
Provides a LAN-accessible dashboard for visualizing water levels, weather, and predictions
"""

import json
import os
import sqlite3
import sys
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
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
    LORA_ENABLED, SMS_ENABLED, DATABASE_PATH
)
from src.config_manager import get_config_dict, apply_config_dict, reset_to_defaults
from src.data.database import (
    get_db_connection, migrate_database,
    get_latest_sensor_data, get_sensor_data_since,
    get_latest_weather, get_weather_since,
    get_latest_prediction, get_predictions_since,
    get_recent_alerts, get_system_status, get_database_stats,
    get_rainfall_since, get_rainfall_stats,
    get_all_alert_contacts, get_alert_contact,
    insert_alert_contact, update_alert_contact, delete_alert_contact,
    get_active_alert_phone_numbers,
    update_system_status
)
from src.data.sms_handler import test_alert_sms
from src.data.lora_receiver import start_lora_receiver_async
from src.model.predict import FloodPredictor
from src.data.weather_fetcher import WeatherFetcher


PREDICTION_INTERVAL_SECONDS = 300
WEATHER_REFRESH_INTERVAL_SECONDS = 21600


# Initialize FastAPI app
app = FastAPI(title="River Monitor Dashboard")

# Mount static files
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")


@app.middleware("http")
async def no_cache_static(request: Request, call_next):
    """Prevent browsers from serving stale static assets.

    Without an explicit Cache-Control header, browsers apply heuristic
    caching (RFC 9111) keyed on Last-Modified/ETag. When index.html is a
    fresh Jinja render but style.css is a heuristically-cached old copy,
    the page ships with mismatched markup/CSS -- e.g. the database page
    collapsing into a single narrow grid cell. "no-cache" forces a
    revalidation round-trip (a 304 when unchanged) instead of stale bytes.
    """
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response

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
        latest_water = get_latest_sensor_data()
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
                "message": "Module disabled" if not SMS_ENABLED else "Alert sending enabled"
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
        water_levels = get_sensor_data_since(hours=hours)
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

        try:
            stored_at = datetime.fromisoformat(prediction['timestamp']) if prediction else None
            fresh = stored_at is not None and (datetime.now() - stored_at).total_seconds() < PREDICTION_INTERVAL_SECONDS * 2
        except (ValueError, TypeError):
            fresh = False

        if not prediction or not fresh:
            fresh_prediction = None
            try:
                predictor = FloodPredictor()
                fresh_prediction = predictor.make_prediction()
            except Exception as pred_err:
                print(f"Fresh prediction failed: {pred_err}")

            if fresh_prediction:
                return JSONResponse(content={
                    'timestamp': fresh_prediction['timestamp'],
                    'current_level_m': fresh_prediction['current_level_m'],
                    'risk_level': fresh_prediction['risk_level'],
                    'risk_level_48h': fresh_prediction.get('risk_level_48h'),
                    'rf_propensity': fresh_prediction.get('rf_propensity', 'Unknown'),
                    'rf_propensity_48h': fresh_prediction.get('rf_propensity_48h', 'Unknown'),
                    'forecast': fresh_prediction['forecast'],
                    'forecast_change_1d': fresh_prediction['forecast_change_1d'],
                    'fuzzy_result': fresh_prediction.get('fuzzy_result', {}),
                    'fuzzy_result_48h': fresh_prediction.get('fuzzy_result_48h', {}),
                    'used_fallback': bool(fresh_prediction.get('fuzzy_result', {}).get('used_fallback')),
                    'used_fallback_48h': bool(fresh_prediction.get('fuzzy_result_48h', {}).get('used_fallback'))
                })

            # No fresh prediction possible: serve the stored (stale) one when it
            # exists, otherwise there is nothing to display yet.
            if not prediction:
                return JSONResponse(content={"error": "No data available yet"}, status_code=409)

        # Format existing prediction
        if isinstance(prediction['forecast_data'], str):
            prediction['forecast_data'] = json.loads(prediction['forecast_data'])
        if isinstance(prediction['fuzzy_inputs'], str):
            prediction['fuzzy_inputs'] = json.loads(prediction['fuzzy_inputs'])
        if isinstance(prediction.get('fuzzy_inputs_48h'), str):
            prediction['fuzzy_inputs_48h'] = json.loads(prediction['fuzzy_inputs_48h'])

        forecast = prediction['forecast_data'] or []
        forecast_change_1d = round(forecast[0] - prediction['current_level_m'], 3) if forecast else 0

        return JSONResponse(content={
            'timestamp': prediction['timestamp'],
            'current_level_m': prediction['current_level_m'],
            'risk_level': prediction['risk_level'],
            'risk_level_48h': prediction.get('risk_level_48h'),
            'rf_propensity': prediction.get('rf_propensity', 'Unknown'),
            'rf_propensity_48h': prediction.get('rf_propensity_48h', 'Unknown'),
            'forecast': forecast,
            'forecast_change_1d': forecast_change_1d,
            'fuzzy_inputs': prediction.get('fuzzy_inputs', {}),
            'fuzzy_inputs_48h': prediction.get('fuzzy_inputs_48h', {}),
            'rule_triggered': prediction.get('rule_triggered'),
            'rule_triggered_48h': prediction.get('rule_triggered_48h'),
            'used_fallback': bool(prediction.get('used_fallback')),
            'used_fallback_48h': bool(prediction.get('used_fallback_48h'))
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
        fuzzy_inputs_48h = prediction.get('fuzzy_inputs_48h', {})
        if isinstance(fuzzy_inputs_48h, str):
            fuzzy_inputs_48h = json.loads(fuzzy_inputs_48h)
        
        # Get rule triggered
        rule_triggered = prediction.get('rule_triggered')
        rule_triggered_48h = prediction.get('rule_triggered_48h')
        
        # Get RF propensity
        rf_propensity = prediction.get('rf_propensity', 'Unknown')
        rf_propensity_48h = prediction.get('rf_propensity_48h', 'Unknown')
        
        # Get current water level for display
        latest_water = get_latest_sensor_data()
        current_water_level_mm = latest_water['water_level_m'] * 1000 if latest_water else 0
        
        # Build detailed response
        details = {
            'timestamp': prediction['timestamp'],
            'risk_level': prediction['risk_level'],
            'risk_level_48h': prediction.get('risk_level_48h'),
            'rf_propensity': rf_propensity,
            'rf_propensity_48h': rf_propensity_48h,
            'rule_triggered': rule_triggered,
            'rule_triggered_48h': rule_triggered_48h,
            'used_fallback': bool(prediction.get('used_fallback')),
            'used_fallback_48h': bool(prediction.get('used_fallback_48h')),
            'current_water_level_mm': current_water_level_mm,
            'fuzzy_inputs': fuzzy_inputs,
            'fuzzy_inputs_48h': fuzzy_inputs_48h,
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
            
            # Return forecast with timestamps (daily, day 1..N ahead of today)
            now = datetime.now()
            forecast_with_timestamps = [
                {
                    'timestamp': (now + timedelta(days=i + 1)).isoformat(),
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
# DATABASE VIEWER API
# ============================================================================

def _db_table_names() -> List[str]:
    """Return user table names from sqlite_master (excludes sqlite_% internals)"""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        return [r['name'] for r in rows]
    finally:
        conn.close()


@app.get("/api/db/tables")
async def db_tables() -> JSONResponse:
    """Get list of database tables with row counts"""
    try:
        conn = get_db_connection()
        try:
            tables = []
            for name in _db_table_names():
                count = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
                tables.append({"name": name, "rows": count})
            return JSONResponse(content={"tables": tables})
        finally:
            conn.close()
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/db/table/{table_name}")
async def db_table_rows(table_name: str, limit: int = 50, offset: int = 0,
                        sort_by: Optional[str] = None, sort_dir: str = "desc") -> JSONResponse:
    """Get paginated rows from a database table"""
    try:
        if table_name not in _db_table_names():
            raise HTTPException(status_code=404, detail=f"Unknown table: {table_name}")

        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        sort_dir = "ASC" if sort_dir.lower() == "asc" else "DESC"

        conn = get_db_connection()
        try:
            columns = [r['name'] for r in conn.execute(f'PRAGMA table_info("{table_name}")')]
            if not sort_by or sort_by not in columns:
                sort_by = columns[0] if columns else "id"
            total = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
            rows = conn.execute(
                f'SELECT * FROM "{table_name}" ORDER BY "{sort_by}" {sort_dir} LIMIT ? OFFSET ?',
                (limit, offset)
            ).fetchall()
            return JSONResponse(content={
                "table": table_name,
                "columns": columns,
                "rows": [dict(r) for r in rows],
                "total": total,
                "limit": limit,
                "offset": offset,
                "sort_by": sort_by,
                "sort_dir": sort_dir.lower()
            })
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/db/download")
async def download_database() -> FileResponse:
    """Download the SQLite database file"""
    db_path = DATABASE_PATH if os.path.isabs(DATABASE_PATH) else os.path.join(_PROJECT_ROOT, DATABASE_PATH)
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database file not found")
    return FileResponse(
        db_path,
        media_type="application/octet-stream",
        filename=os.path.basename(db_path)
    )


# ============================================================================
# WEB HOOKS FOR MANUAL ACTIONS
# ============================================================================

@app.post("/api/refresh-prediction")
async def refresh_prediction() -> JSONResponse:
    """Manually trigger a new prediction"""
    try:
        from src.model.predict import predict_and_alert
        prediction = predict_and_alert()

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


def _restart_dashboard() -> None:
    """Re-exec the dashboard process in-place after a short delay.

    Runs in a background thread so the HTTP response flushes first.
    Under systemd (Restart=always) an os._exit fallback is safe because
    the service supervisor brings the process right back.
    """
    time.sleep(1.2)
    try:
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        print(f"Restart failed, exiting for supervisor: {e}")
        os._exit(0)


@app.post("/api/restart")
async def restart_server() -> JSONResponse:
    try:
        t = threading.Thread(target=_restart_dashboard, name="dashboard-restart", daemon=True)
        t.start()
        return JSONResponse(content={"status": "restarting"})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# ============================================================================
# MAIN
# ============================================================================

def _background_scheduler() -> None:
    """Periodically refresh weather, run predictions (which auto-alerts),
    and record component status. Runs as a daemon thread so a failure in any
    action never terminates the dashboard."""
    last_weather_refresh = time.monotonic()
    last_prediction = time.monotonic()

    while True:
        try:
            now = time.monotonic()

            if now - last_weather_refresh >= WEATHER_REFRESH_INTERVAL_SECONDS:
                try:
                    fetcher = WeatherFetcher()
                    if fetcher.store_weather_in_db():
                        update_system_status('weather', 'ok', 'Weather data refreshed')
                    else:
                        update_system_status('weather', 'warning', 'Weather refresh returned no data')
                except Exception as e:
                    update_system_status('weather', 'error', str(e))
                last_weather_refresh = now

            if now - last_prediction >= PREDICTION_INTERVAL_SECONDS:
                try:
                    from src.model.predict import predict_and_alert
                    prediction = predict_and_alert()
                    if prediction:
                        update_system_status('model', 'ok', 'Prediction updated')
                    else:
                        update_system_status('model', 'warning', 'Prediction failed (no data?)')
                except Exception as e:
                    update_system_status('model', 'error', str(e))
                last_prediction = now

            try:
                latest_water = get_latest_sensor_data()
                if latest_water and (datetime.now() - datetime.fromisoformat(latest_water['timestamp'])).total_seconds() < 300:
                    update_system_status('lora', 'ok', 'Receiving data')
                elif latest_water:
                    update_system_status('lora', 'warning', 'No recent LoRa data')
                else:
                    update_system_status('lora', 'error', 'No LoRa data')
            except Exception as e:
                update_system_status('lora', 'error', str(e))
        except Exception as e:
            print(f"Background scheduler error: {e}")

        time.sleep(60)


def run_dashboard():
    """Run the FastAPI dashboard server"""
    print(f"Starting River Monitor Dashboard on {DASHBOARD_HOST}:{DASHBOARD_PORT}")
    print(f"Access the dashboard at: http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")

    # Run any pending schema migrations (idempotent: only adds missing
    # tables/columns from older DB versions). Must run before the
    # background prediction scheduler, which writes risk_level_48h etc.
    try:
        migrate_database()
    except Exception as e:
        print(f"Warning: Database migration failed at startup: {e}")

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

    # Start the periodic weather/prediction scheduler as a daemon thread.
    threading.Thread(target=_background_scheduler, name="background-scheduler", daemon=True).start()

    uvicorn.run(
        app,
        host=DASHBOARD_HOST,
        port=DASHBOARD_PORT,
        reload=False  # Disable reload in production
    )


if __name__ == "__main__":
    run_dashboard()