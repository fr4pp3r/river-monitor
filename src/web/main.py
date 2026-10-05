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

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
from loguru import logger

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
from src.settings import settings
from src.logging_config import setup_logging
from src.config_manager import get_config_dict, apply_config_dict, reset_to_defaults, validate_config_dict
from src.data.database import (
    get_db_connection, migrate_database,
    get_latest_sensor_data, get_sensor_data_since,
    get_latest_weather, get_weather_since,
    get_latest_prediction, get_predictions_since,
    get_recent_alerts, get_alerts_filtered, get_alert, acknowledge_alert, get_alert_ack_stats,
    get_system_status, get_database_stats, get_sensor_health,
    get_rainfall_since, get_rainfall_stats,
    rebuild_rainfall_daily,
    get_all_alert_contacts, get_alert_contact,
    insert_alert_contact, update_alert_contact, delete_alert_contact,
    get_active_alert_phone_numbers,
    update_system_status,
    count_users, insert_user, get_user, get_user_by_username, list_users, update_user, delete_user,
    log_audit, get_audit_log,
)
from src.web.auth import (
    hash_password, authenticate_user, ensure_default_admin, login_user, logout_user,
    session_user, is_admin, require_admin, is_public_path,
)
from src.data.sms_handler import test_alert_sms
from src.data.lora_receiver import start_lora_receiver_async
from src.model.predict import FloodPredictor
from src.data.weather_fetcher import WeatherFetcher


PREDICTION_INTERVAL_SECONDS = 300
WEATHER_REFRESH_INTERVAL_SECONDS = 21600


# Initialize FastAPI app
setup_logging()
try:
    ensure_default_admin()
except Exception as e:
    logger.warning(f"Could not ensure default admin account: {e}")
if settings.auth_enabled and settings.secret_key == "change-me-in-production-river-monitor":
    logger.warning("SECRET_KEY is the insecure default; set SECRET_KEY in .env before deployment")
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

@app.middleware("http")
async def auth_guard(request: Request, call_next):
    path = request.url.path
    if not settings.auth_enabled or is_public_path(path):
        return await call_next(request)

    user = session_user(request)
    if not user:
        if path.startswith("/api/"):
            return JSONResponse(content={"error": "Authentication required"}, status_code=401)
        return RedirectResponse("/login")

    if request.method in ("POST", "PUT", "DELETE", "PATCH") and user.get("role") != "admin":
        return JSONResponse(content={"error": "Administrator role required"}, status_code=403)

    return await call_next(request)


# Added last so it is the outermost middleware: it must populate
# request.session before auth_guard reads it.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    max_age=settings.session_max_age_seconds,
    same_site="lax",
    https_only=False,
)

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


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if settings.auth_enabled and session_user(request):
        return RedirectResponse("/")
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/api/auth/login")
async def auth_login(request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(content={"error": "Invalid JSON body"}, status_code=400)

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    user = authenticate_user(username, password)
    if not user:
        log_audit("login_failed", actor=username,
                  ip_address=request.client.host if request.client else None)
        return JSONResponse(content={"error": "Invalid credentials"}, status_code=401)

    login_user(request, user)
    return JSONResponse(content={"status": "success", "username": user["username"], "role": user["role"]})


@app.post("/api/auth/logout")
async def auth_logout(request: Request) -> JSONResponse:
    logout_user(request)
    return JSONResponse(content={"status": "success"})


@app.get("/api/auth/me")
async def auth_me(request: Request) -> JSONResponse:
    user = session_user(request)
    return JSONResponse(content={
        "auth_enabled": settings.auth_enabled,
        "authenticated": bool(user),
        "username": user.get("username") if user else None,
        "role": user.get("role") if user else None,
    })


@app.get("/healthz")
async def healthz() -> JSONResponse:
    """Liveness probe: the process is up and able to serve requests."""
    return JSONResponse(content={"status": "ok"})


@app.get("/readyz")
async def readyz() -> JSONResponse:
    """Readiness probe: database, model artifacts and weather data are usable."""
    checks = {}

    try:
        conn = get_db_connection()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        checks["database"] = {"ok": True}
    except Exception as e:
        checks["database"] = {"ok": False, "error": str(e)}

    model_path = os.path.join(_PROJECT_ROOT, "data/models/rf_model.pkl")
    scaler_path = os.path.join(_PROJECT_ROOT, "data/models/scaler.pkl")
    checks["model"] = {
        "ok": os.path.exists(model_path),
        "model_file": os.path.exists(model_path),
        "scaler_file": os.path.exists(scaler_path),
    }

    try:
        age_seconds = weather_age(get_latest_weather())
        checks["weather"] = {
            "ok": age_seconds is not None and age_seconds <= config_module.WEATHER_STALE_AFTER,
            "age_seconds": round(age_seconds, 1) if age_seconds is not None else None,
        }
    except Exception as e:
        checks["weather"] = {"ok": False, "error": str(e)}

    ready = all(check.get("ok") for check in checks.values())
    return JSONResponse(content={"status": "ready" if ready else "degraded", "checks": checks},
                        status_code=200 if ready else 503)


@app.get("/api/sensor-health")
async def sensor_health(window_hours: int = 24) -> JSONResponse:
    try:
        expected = max(1, int(3600 / max(1, config_module.WATER_LEVEL_INTERVAL)))
        return JSONResponse(content=get_sensor_health(window_hours=window_hours,
                                                     expected_interval_seconds=expected))
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


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
        
        weather_age_seconds = weather_age(latest_weather)
        weather_stale = latest_weather is None or weather_age_seconds is None \
            or weather_age_seconds > config_module.WEATHER_STALE_AFTER
        
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
                "status": "warning" if weather_stale else "ok",
                "last_update": latest_weather['timestamp'] if latest_weather else None,
                "age_seconds": round(weather_age_seconds, 1) if weather_age_seconds is not None else None,
                "stale": weather_stale,
                "message": weather_status_message(latest_weather, weather_age_seconds, weather_stale)
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
                # Tag the fallback so the UI can flag that it is not a
                # recent reading rather than presenting it as current
                age_seconds = weather_age(latest)
                latest['age_seconds'] = round(age_seconds, 1) if age_seconds is not None else None
                latest['stale'] = (age_seconds is None
                                   or age_seconds > config_module.WEATHER_STALE_AFTER)
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
                logger.warning(f"Fresh prediction failed: {pred_err}")

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
async def get_alerts(limit: int = 50, risk_level: Optional[str] = None,
                     status: Optional[str] = None, acknowledged: Optional[bool] = None,
                     start: Optional[str] = None, end: Optional[str] = None) -> JSONResponse:
    """Get alerts with optional risk-level, status, acknowledgement and date filters."""
    try:
        start_dt = datetime.fromisoformat(start) if start else None
        end_dt = datetime.fromisoformat(end) if end else None
    except ValueError:
        return JSONResponse(content={"error": "Invalid start/end date (expected ISO 8601)"}, status_code=400)

    try:
        alerts = get_alerts_filtered(
            limit=limit, risk_level=risk_level, status=status,
            acknowledged=acknowledged, start=start_dt, end=end_dt,
        )
        return JSONResponse(content=[dict(a) for a in alerts])
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/alerts/stats")
async def alert_stats() -> JSONResponse:
    try:
        return JSONResponse(content=get_alert_ack_stats())
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/alerts/{alert_id}")
async def get_alert_by_id(alert_id: int) -> JSONResponse:
    try:
        alert = get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        return JSONResponse(content=alert)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert_endpoint(alert_id: int, request: Request) -> JSONResponse:
    try:
        user = session_user(request) or {"username": "anonymous"}
        ok = acknowledge_alert(alert_id, actor=user.get("username", "anonymous"))
        if not ok:
            raise HTTPException(status_code=404, detail="Alert not found")
        log_audit("alert_acknowledge", actor=user.get("username"), role=user.get("role"),
                  target=str(alert_id), ip_address=request.client.host if request.client else None)
        return JSONResponse(content={"status": "success", "alert_id": alert_id,
                                     "acknowledged_by": user.get("username")})
    except HTTPException:
        raise
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
async def refresh_prediction(request: Request) -> JSONResponse:
    """Manually trigger a new prediction"""
    try:
        from src.model.predict import predict_and_alert
        prediction = predict_and_alert()

        user = session_user(request) or {}
        log_audit("refresh_prediction", actor=user.get("username"), role=user.get("role"),
                  ip_address=request.client.host if request.client else None)

        if prediction:
            return JSONResponse(content={
                "status": "success",
                "prediction": prediction
            })
        else:
            return JSONResponse(content={"status": "error", "message": "Failed to make prediction"}, status_code=500)

    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/refresh-rainfall")
async def refresh_rainfall(request: Request) -> JSONResponse:
    """Recompute daily rainfall totals from stored sensor readings"""
    try:
        result = rebuild_rainfall_daily()
        user = session_user(request) or {}
        log_audit("refresh_rainfall", actor=user.get("username"), role=user.get("role"),
                  ip_address=request.client.host if request.client else None)
        return JSONResponse(content={"status": "success", **result})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/refresh-weather")
async def refresh_weather(request: Request) -> JSONResponse:
    """Refetch the weather + tidal forecast from Open-Meteo, bypassing the cache"""
    try:
        stored = refresh_weather_tide_cache()
        user = session_user(request) or {}
        log_audit("refresh_weather", actor=user.get("username"), role=user.get("role"),
                  ip_address=request.client.host if request.client else None)

        if not stored:
            return JSONResponse(
                content={"status": "error",
                         "message": "Open-Meteo returned no forecast data (network or upstream failure)"},
                status_code=502)

        dates: list = []
        latest = get_latest_weather()
        if latest and latest.get("forecast_data"):
            try:
                parsed = json.loads(latest["forecast_data"])
            except (json.JSONDecodeError, TypeError):
                parsed = None
            if isinstance(parsed, list):
                dates = [d.get("date") for d in parsed if isinstance(d, dict) and d.get("date")]

        return JSONResponse(content={
            "status": "success",
            "forecast_start": dates[0] if dates else None,
            "forecast_end": dates[-1] if dates else None,
            "forecast_days": len(dates),
        })
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/test-alert")
async def test_alert(request: Request) -> JSONResponse:
    """Test SMS alert system"""
    if not SMS_ENABLED:
        return JSONResponse(content={"status": "error", "message": "SMS module is disabled in config"}, status_code=400)
    
    try:
        from src.data.sms_handler import test_alert_sms
        
        success = test_alert_sms()
        user = session_user(request) or {}
        log_audit("test_alert", actor=user.get("username"), role=user.get("role"),
                  details="sent" if success else "failed",
                  ip_address=request.client.host if request.client else None)
        
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
        user = session_user(request) or {}
        log_audit("contact_create", actor=user.get("username"), role=user.get("role"),
                  target=name, ip_address=request.client.host if request.client else None)
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
            user = session_user(request) or {}
            log_audit("contact_update", actor=user.get("username"), role=user.get("role"),
                      target=str(contact_id), details=",".join(updates.keys()),
                      ip_address=request.client.host if request.client else None)
            return JSONResponse(content={"status": "success"})
        else:
            return JSONResponse(content={"error": "Contact not found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.delete("/api/contacts/{contact_id}")
async def delete_contact(contact_id: int, request: Request) -> JSONResponse:
    """Delete an alert contact"""
    try:
        success = delete_alert_contact(contact_id)
        
        if success:
            user = session_user(request) or {}
            log_audit("contact_delete", actor=user.get("username"), role=user.get("role"),
                      target=str(contact_id), ip_address=request.client.host if request.client else None)
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
        user = session_user(request) or {}
        ok, err = apply_config_dict(data)
        if ok:
            log_audit("config_update", actor=user.get("username"), role=user.get("role"),
                      target=",".join(sorted(data.keys())),
                      ip_address=request.client.host if request.client else None)
            return JSONResponse(content={"status": "success"})
        return JSONResponse(content={"error": err}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/config/reset")
async def reset_config(request: Request) -> JSONResponse:
    try:
        user = session_user(request) or {}
        ok, err = reset_to_defaults()
        if ok:
            log_audit("config_reset", actor=user.get("username"), role=user.get("role"),
                      target="all", ip_address=request.client.host if request.client else None)
            return JSONResponse(content={"status": "success"})
        return JSONResponse(content={"error": err}, status_code=500)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# ============================================================================
# USER MANAGEMENT API (admin only)
# ============================================================================

@app.get("/api/users")
async def users_list(_: dict = Depends(require_admin)) -> JSONResponse:
    try:
        return JSONResponse(content=list_users())
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/users")
async def users_create(request: Request, user: dict = Depends(require_admin)) -> JSONResponse:
    try:
        data = await request.json()
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        role = data.get("role", "viewer")
        if not username or not password:
            return JSONResponse(content={"error": "username and password are required"}, status_code=400)
        if role not in ("viewer", "admin"):
            return JSONResponse(content={"error": "role must be 'viewer' or 'admin'"}, status_code=400)
        if get_user_by_username(username):
            return JSONResponse(content={"error": "username already exists"}, status_code=409)

        user_id = insert_user(username, hash_password(password), role=role)
        log_audit("user_create", actor=user.get("username"), role=user.get("role"),
                  target=username, ip_address=request.client.host if request.client else None)
        return JSONResponse(content={"status": "success", "user_id": user_id})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.put("/api/users/{user_id}")
async def users_update(user_id: int, request: Request, user: dict = Depends(require_admin)) -> JSONResponse:
    try:
        data = await request.json()
        updates = {}
        if "role" in data:
            if data["role"] not in ("viewer", "admin"):
                return JSONResponse(content={"error": "role must be 'viewer' or 'admin'"}, status_code=400)
            updates["role"] = data["role"]
        if "is_active" in data:
            updates["is_active"] = 1 if data["is_active"] else 0
        if "password" in data and data["password"]:
            updates["password_hash"] = hash_password(data["password"])
        if not updates:
            return JSONResponse(content={"error": "No valid fields to update"}, status_code=400)

        if not update_user(user_id, **updates):
            raise HTTPException(status_code=404, detail="User not found")
        log_audit("user_update", actor=user.get("username"), role=user.get("role"),
                  target=str(user_id), details=",".join(updates.keys()),
                  ip_address=request.client.host if request.client else None)
        return JSONResponse(content={"status": "success"})
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.delete("/api/users/{user_id}")
async def users_delete(user_id: int, request: Request, user: dict = Depends(require_admin)) -> JSONResponse:
    try:
        if user.get("user_id") == user_id:
            return JSONResponse(content={"error": "Cannot delete your own account"}, status_code=400)
        if not delete_user(user_id):
            raise HTTPException(status_code=404, detail="User not found")
        log_audit("user_delete", actor=user.get("username"), role=user.get("role"),
                  target=str(user_id), ip_address=request.client.host if request.client else None)
        return JSONResponse(content={"status": "success"})
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/audit")
async def audit_log_list(limit: int = 100, _: dict = Depends(require_admin)) -> JSONResponse:
    try:
        return JSONResponse(content=get_audit_log(limit=limit))
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
        logger.error(f"Restart failed, exiting for supervisor: {e}")
        os._exit(0)


@app.post("/api/restart")
async def restart_server(request: Request) -> JSONResponse:
    try:
        user = session_user(request) or {}
        log_audit("restart", actor=user.get("username"), role=user.get("role"),
                  ip_address=request.client.host if request.client else None)
        t = threading.Thread(target=_restart_dashboard, name="dashboard-restart", daemon=True)
        t.start()
        return JSONResponse(content={"status": "restarting"})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# ============================================================================
# MAIN
# ============================================================================

def weather_age(weather: Optional[Dict]) -> Optional[float]:
    """Age in seconds of a weather record, or None if absent/unparseable."""
    if not weather:
        return None
    try:
        return (datetime.now() - datetime.fromisoformat(weather['timestamp'])).total_seconds()
    except (KeyError, TypeError, ValueError):
        return None


def weather_status_message(weather: Optional[Dict], age_seconds: Optional[float], stale: bool) -> str:
    """Operator-facing description of the stored forecast's freshness."""
    if not weather:
        return "No weather data"
    if age_seconds is None:
        return "Unreadable weather timestamp"
    if stale:
        return f"Stale forecast ({age_seconds / 3600:.1f}h old)"
    return "Data available"


def refresh_weather_tide_cache() -> bool:
    """Fetch fresh weather + tide data from Open-Meteo and store it (DB + file cache)."""
    fetcher = WeatherFetcher()
    ok = fetcher.store_weather_in_db()
    update_system_status('weather', 'ok' if ok else 'warning',
                         'Weather data refreshed' if ok else 'Weather refresh returned no data')
    return ok


def _background_scheduler() -> None:
    """Periodically refresh weather, run predictions (which auto-alerts),
    and record component status. Runs as a daemon thread so a failure in any
    action never terminates the dashboard.

    Both timers start already elapsed so the first pass refreshes immediately
    rather than waiting a full interval; otherwise a process restarted more
    often than the interval never refreshes at all.
    """
    last_weather_refresh = time.monotonic() - WEATHER_REFRESH_INTERVAL_SECONDS
    last_prediction = time.monotonic() - PREDICTION_INTERVAL_SECONDS

    while True:
        try:
            now = time.monotonic()

            if now - last_weather_refresh >= WEATHER_REFRESH_INTERVAL_SECONDS:
                try:
                    if not refresh_weather_tide_cache():
                        logger.warning("Scheduled weather refresh returned no data")
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
            logger.error(f"Background scheduler error: {e}")

        time.sleep(60)


def run_dashboard():
    """Run the FastAPI dashboard server"""
    logger.info(f"Starting River Monitor Dashboard on {DASHBOARD_HOST}:{DASHBOARD_PORT}")
    logger.info(f"Access the dashboard at: http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")

    # Run any pending schema migrations (idempotent: only adds missing
    # tables/columns from older DB versions). Must run before the
    # background prediction scheduler, which writes risk_level_48h etc.
    try:
        migrate_database()
    except Exception as e:
        logger.warning(f"Database migration failed at startup: {e}")

    # Try to fetch and store fresh weather/tide data so the dashboard has
    # up-to-date readings even before the first sensor packet arrives.
    try:
        if refresh_weather_tide_cache():
            logger.info("Weather and tide data refreshed at startup")
        else:
            logger.warning("Could not refresh weather data at startup (using cached/last known)")
    except Exception as e:
        logger.warning(f"Weather refresh at startup failed: {e}")

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