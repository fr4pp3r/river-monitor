"""
Database operations for River Monitor System
Handles SQLite database for water levels, weather data, predictions, and alerts
"""

import sqlite3
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager

# Ensure the project root is on the module search path so that
# "from src.config import ..." styles of absolute imports work
# regardless of the directory this script is invoked from.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.config import DATABASE_PATH


def get_db_connection():
    """Get a database connection with row factory for dict-like access"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_transaction():
    """Context manager for database transactions"""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Initialize database tables if they don't exist"""
    with db_transaction() as conn:
        cursor = conn.cursor()
        
        # Sensor readings table (water level + rainfall per LoRa/SMS packet)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                water_level_m REAL NOT NULL,
                raw_distance_m REAL NOT NULL,
                raw_distance_mm INTEGER,
                rain_tips INTEGER DEFAULT 0,
                rainfall_mm REAL,
                source TEXT NOT NULL CHECK (source IN ('lora', 'sms'))
            )
        """)

        # Hourly tide level readings (from Open-Meteo marine API)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tidal_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                tide_level_m REAL NOT NULL
            )
        """)

        # Daily rainfall totals (one row per calendar day, 'YYYY-MM-DD')
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rainfall_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                total_tips INTEGER DEFAULT 0,
                total_rainfall_mm REAL DEFAULT 0.0,
                created_at DATETIME DEFAULT (datetime('now', '+8 hours'))
            )
        """)
        
        # Weather data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                precipitation_mm REAL,
                temperature_max_c REAL,
                temperature_min_c REAL,
                tide_max_m REAL,
                tide_min_m REAL,
                pressure_hpa REAL,
                temperature_c REAL,
                humidity_percent REAL,
                wind_speed_ms REAL,
                wind_direction_deg REAL,
                forecast_data TEXT,  -- JSON string of forecast
                tide_forecast_data TEXT  -- JSON string of tide forecast
            )
        """)
        
        # Predictions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                current_level_m REAL NOT NULL,
                risk_level TEXT NOT NULL,
                risk_level_48h TEXT,
                rf_propensity TEXT,  -- 'Low', 'Medium', 'High'
                rf_propensity_48h TEXT,  -- 'Low', 'Medium', 'High'
                fuzzy_inputs TEXT,   -- JSON of WL, RoR, FRain, Tide, RF
                fuzzy_inputs_48h TEXT,   -- JSON of WL, RoR, FRain, Tide, RF
                rule_triggered INTEGER,  -- Which rule fired (1-20)
                rule_triggered_48h INTEGER,  -- Which rule fired (1-20)
                used_fallback INTEGER DEFAULT 0,  -- 1 if fallback scoring used (no fuzzy rule matched)
                used_fallback_48h INTEGER DEFAULT 0,
                forecast_data TEXT NOT NULL,  -- JSON array of 7 daily predictions
                model_version TEXT
            )
        """)
        
        # Alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                risk_level TEXT NOT NULL,
                water_level_m REAL NOT NULL,
                message TEXT NOT NULL,
                sent_to TEXT,  -- Comma-separated phone numbers
                status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
                acknowledged INTEGER DEFAULT 0,
                acknowledged_by TEXT,
                acknowledged_at DATETIME
            )
        """)

        # Users table (dashboard authentication + roles)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('viewer', 'admin')),
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT (datetime('now', '+8 hours')),
                updated_at DATETIME DEFAULT (datetime('now', '+8 hours')),
                last_login DATETIME
            )
        """)

        # Audit log table (who did what, when)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                actor TEXT,
                role TEXT,
                action TEXT NOT NULL,
                target TEXT,
                details TEXT,
                ip_address TEXT
            )
        """)
        
        # Alert contacts table (phone numbers for SMS alerts)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone_number TEXT NOT NULL UNIQUE,
                is_active INTEGER DEFAULT 1,
                receive_alert INTEGER DEFAULT 1,
                receive_warning INTEGER DEFAULT 1,
                receive_critical INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT (datetime('now', '+8 hours')),
                updated_at DATETIME DEFAULT (datetime('now', '+8 hours'))
            )
        """)
        
        # System status table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                component TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('ok', 'warning', 'error')),
                message TEXT
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp ON sensor_data(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tidal_data_timestamp ON tidal_data(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rainfall_daily_date ON rainfall_daily(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_weather_data_timestamp ON weather_data(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_status_timestamp ON system_status(timestamp)")
        
        # Rainfall aggregation table (for hourly/daily totals)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rainfall_hourly (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                hour INTEGER NOT NULL,
                day INTEGER NOT NULL,
                month INTEGER NOT NULL,
                year INTEGER NOT NULL,
                total_tips INTEGER DEFAULT 0,
                total_rainfall_mm REAL DEFAULT 0.0,
                UNIQUE(hour, day, month, year)
            )
        """)


# ============================================================================
# SENSOR DATA OPERATIONS
# ============================================================================

def insert_sensor_data(timestamp: datetime, water_level_m: float, raw_distance_m: float, 
                        raw_distance_mm: int = None, rain_tips: int = 0, rainfall_mm: float = 0.0, 
                        source: str = "lora") -> int:
    """Insert a sensor data reading"""
    with db_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sensor_data 
            (timestamp, water_level_m, raw_distance_m, raw_distance_mm, rain_tips, rainfall_mm, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (timestamp.isoformat(), water_level_m, raw_distance_m, raw_distance_mm, rain_tips, rainfall_mm, source))
        return cursor.lastrowid


def get_latest_sensor_data() -> Optional[Dict]:
    """Get the most recent sensor data reading"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM sensor_data 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        row = cursor.fetchone()
        return dict(row) if row else None


def get_sensor_data_since(hours: int = 24) -> List[Dict]:
    """Get sensor data readings from the last N hours"""
    since = datetime.now() - timedelta(hours=hours)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM sensor_data 
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (since.isoformat(),))
        return [dict(row) for row in cursor.fetchall()]


def get_sensor_data_range(start: datetime, end: datetime) -> List[Dict]:
    """Get sensor data readings within a time range"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM sensor_data 
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC
        """, (start.isoformat(), end.isoformat()))
        return [dict(row) for row in cursor.fetchall()]


def get_sensor_data_stats(hours: int = 24) -> Dict:
    """Get statistics for sensor data in the last N hours"""
    since = datetime.now() - timedelta(hours=hours)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                MIN(water_level_m) as min_level,
                MAX(water_level_m) as max_level,
                AVG(water_level_m) as avg_level,
                COUNT(*) as count
            FROM sensor_data 
            WHERE timestamp >= ?
        """, (since.isoformat(),))
        row = cursor.fetchone()
        return dict(row) if row else {}


# ============================================================================
# WEATHER DATA OPERATIONS
# ============================================================================

def insert_weather_data(timestamp: datetime, data: Dict) -> int:
    """Insert weather data"""
    with db_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO weather_data 
            (timestamp, precipitation_mm, temperature_max_c, temperature_min_c, 
             tide_max_m, tide_min_m, pressure_hpa, temperature_c, 
             humidity_percent, wind_speed_ms, wind_direction_deg, forecast_data, tide_forecast_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp.isoformat(),
            data.get('precipitation_mm'),
            data.get('temperature_max_c'),
            data.get('temperature_min_c'),
            data.get('tide_max_m'),
            data.get('tide_min_m'),
            data.get('pressure_hpa'),
            data.get('temperature_c'),
            data.get('humidity_percent'),
            data.get('wind_speed_ms'),
            data.get('wind_direction_deg'),
            data.get('forecast_data'),
            data.get('tide_forecast_data')
        ))
        return cursor.lastrowid


def get_latest_weather(max_age_seconds: Optional[float] = None) -> Optional[Dict]:
    """Get the most recent weather data.

    Pass max_age_seconds to treat rows older than that as absent, so a caller
    never silently consumes an expired forecast.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM weather_data 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        row = cursor.fetchone()
        if not row:
            return None

        record = dict(row)
        if max_age_seconds is None:
            return record

        try:
            age_seconds = (datetime.now() - datetime.fromisoformat(record['timestamp'])).total_seconds()
        except (KeyError, TypeError, ValueError):
            return None
        return record if age_seconds <= max_age_seconds else None


def get_weather_since(hours: int = 48) -> List[Dict]:
    """Get weather data from the last N hours"""
    since = datetime.now() - timedelta(hours=hours)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM weather_data 
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (since.isoformat(),))
        return [dict(row) for row in cursor.fetchall()]


# ============================================================================
# PREDICTION OPERATIONS
# ============================================================================

def insert_prediction(timestamp: datetime, current_level_m: float, 
                      risk_level: str, forecast_data: list, model_version: str = "1.0",
                      rf_propensity: str = None, fuzzy_inputs: dict = None, rule_triggered: int = None,
                      risk_level_48h: str = None, rf_propensity_48h: str = None,
                      fuzzy_inputs_48h: dict = None, rule_triggered_48h: int = None,
                      used_fallback: int = None, used_fallback_48h: int = None) -> int:
    """Insert a prediction"""
    import json
    with db_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO predictions (timestamp, current_level_m, risk_level, risk_level_48h,
                                     rf_propensity, rf_propensity_48h, fuzzy_inputs, fuzzy_inputs_48h,
                                     rule_triggered, rule_triggered_48h, used_fallback, used_fallback_48h,
                                     forecast_data, model_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp.isoformat(), current_level_m, risk_level, risk_level_48h,
              rf_propensity, rf_propensity_48h,
              json.dumps(fuzzy_inputs) if fuzzy_inputs else None,
              json.dumps(fuzzy_inputs_48h) if fuzzy_inputs_48h else None,
              rule_triggered, rule_triggered_48h,
              used_fallback, used_fallback_48h,
              json.dumps(forecast_data), model_version))
        return cursor.lastrowid


def get_latest_prediction() -> Optional[Dict]:
    """Get the most recent prediction"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM predictions 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            result = dict(row)
            import json
            result['forecast_data'] = json.loads(result['forecast_data']) if result['forecast_data'] else []
            result['fuzzy_inputs'] = json.loads(result['fuzzy_inputs']) if result['fuzzy_inputs'] else {}
            result['fuzzy_inputs_48h'] = json.loads(result['fuzzy_inputs_48h']) if result['fuzzy_inputs_48h'] else {}
            return result
        return None


def get_predictions_since(hours: int = 48) -> List[Dict]:
    """Get predictions from the last N hours"""
    since = datetime.now() - timedelta(hours=hours)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM predictions 
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (since.isoformat(),))
        results = []
        import json
        for row in cursor.fetchall():
            result = dict(row)
            result['forecast_data'] = json.loads(result['forecast_data'])
            results.append(result)
        return results


# ============================================================================
# ALERT OPERATIONS
# ============================================================================

def insert_alert(timestamp: datetime, risk_level: str, water_level_m: float, 
                 message: str, sent_to: str = None, status: str = 'pending') -> int:
    """Insert an alert record"""
    with db_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alerts (timestamp, risk_level, water_level_m, message, sent_to, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (timestamp.isoformat(), risk_level, water_level_m, message, sent_to, status))
        return cursor.lastrowid


def update_alert_status(alert_id: int, status: str):
    """Update alert status"""
    with db_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE alerts SET status = ? WHERE id = ?", (status, alert_id))


def get_recent_alerts(limit: int = 50) -> List[Dict]:
    """Get recent alerts"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM alerts 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_alerts_filtered(limit: int = 50, risk_level: Optional[str] = None,
                        status: Optional[str] = None, acknowledged: Optional[bool] = None,
                        start: Optional[datetime] = None, end: Optional[datetime] = None) -> List[Dict]:
    """Get alerts with optional filters for risk level, send status, ack state and date range."""
    clauses = []
    params: List = []

    if risk_level:
        clauses.append("LOWER(risk_level) = ?")
        params.append(risk_level.strip().lower())
    if status:
        clauses.append("status = ?")
        params.append(status.strip().lower())
    if acknowledged is not None:
        clauses.append("COALESCE(acknowledged, 0) = ?")
        params.append(1 if acknowledged else 0)
    if start is not None:
        clauses.append("timestamp >= ?")
        params.append(start.isoformat())
    if end is not None:
        clauses.append("timestamp <= ?")
        params.append(end.isoformat())

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(max(1, min(limit, 500)))

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT * FROM alerts
            {where}
            ORDER BY timestamp DESC
            LIMIT ?
        """, params)
        return [dict(row) for row in cursor.fetchall()]


def get_alert(alert_id: int) -> Optional[Dict]:
    """Get a single alert by ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def acknowledge_alert(alert_id: int, actor: str) -> bool:
    """Mark an alert acknowledged by the given operator."""
    with db_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE alerts
            SET acknowledged = 1, acknowledged_by = ?, acknowledged_at = ?
            WHERE id = ?
        """, (actor, datetime.now().isoformat(), alert_id))
        return cursor.rowcount > 0


def get_alert_ack_stats() -> Dict:
    """Counts of acknowledged vs outstanding alerts"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN COALESCE(acknowledged, 0) = 1 THEN 1 ELSE 0 END) AS acknowledged,
                SUM(CASE WHEN COALESCE(acknowledged, 0) = 0 THEN 1 ELSE 0 END) AS outstanding
            FROM alerts
        """)
        row = cursor.fetchone()
        stats = dict(row) if row else {}
        stats['total'] = stats.get('total') or 0
        stats['acknowledged'] = stats.get('acknowledged') or 0
        stats['outstanding'] = stats.get('outstanding') or 0
        return stats


# ============================================================================
# USER OPERATIONS (dashboard authentication)
# ============================================================================

def count_users() -> int:
    """Number of dashboard users"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]


def insert_user(username: str, password_hash: str, role: str = "viewer") -> int:
    """Insert a new dashboard user"""
    with db_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, is_active)
            VALUES (?, ?, ?, 1)
        """, (username, password_hash, role))
        return cursor.lastrowid


def get_user_by_username(username: str) -> Optional[Dict]:
    """Get a user by username (includes password_hash for auth checks)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user(user_id: int) -> Optional[Dict]:
    """Get a user by ID (password_hash removed for safe exposure)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        user = dict(row)
        user.pop('password_hash', None)
        return user


def list_users() -> List[Dict]:
    """List all dashboard users without password hashes"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, role, is_active, created_at, updated_at, last_login
            FROM users ORDER BY username
        """)
        return [dict(row) for row in cursor.fetchall()]


def update_user(user_id: int, **kwargs) -> bool:
    """Update a user's role, active flag or password hash"""
    allowed_fields = ['username', 'role', 'is_active', 'password_hash', 'last_login']
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    if not updates:
        return False
    updates['updated_at'] = datetime.now().isoformat()

    with db_transaction() as conn:
        cursor = conn.cursor()
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [user_id]
        cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
        return cursor.rowcount > 0


def delete_user(user_id: int) -> bool:
    """Delete a dashboard user"""
    with db_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        return cursor.rowcount > 0


# ============================================================================
# AUDIT LOG OPERATIONS
# ============================================================================

def log_audit(action: str, actor: Optional[str] = None, role: Optional[str] = None,
              target: Optional[str] = None, details: Optional[str] = None,
              ip_address: Optional[str] = None) -> int:
    """Record a user/system action for accountability"""
    with db_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log (timestamp, actor, role, action, target, details, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), actor, role, action, target, details, ip_address))
        return cursor.lastrowid


def get_audit_log(limit: int = 100) -> List[Dict]:
    """Get the most recent audit log entries"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?
        """, (max(1, min(limit, 500)),))
        return [dict(row) for row in cursor.fetchall()]


# ============================================================================
# SENSOR HEALTH
# ============================================================================

def get_sensor_health(window_hours: int = 24, expected_interval_seconds: int = 60) -> Dict:
    """Summarise sensor link health: freshness, throughput and gaps.

    Computes how old the newest reading is, how many readings arrived in the
    last hour versus how many were expected at the configured cadence, and the
    largest gap between consecutive readings over the window. This lets the
    dashboard distinguish "no data yet" from "sensor dropped out mid-storm".
    """
    now = datetime.now()
    since = now - timedelta(hours=window_hours)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, water_level_m, rainfall_mm, source
            FROM sensor_data
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (since.isoformat(),))
        rows = cursor.fetchall()

    readings = [dict(r) for r in rows]
    latest = readings[-1] if readings else None

    age_seconds = None
    if latest:
        try:
            age_seconds = max(0.0, (now - datetime.fromisoformat(latest['timestamp'])).total_seconds())
        except (ValueError, TypeError):
            age_seconds = None

    cutoff_hour = now - timedelta(hours=1)
    last_hour = [
        r for r in readings
        if _parse_ts(r['timestamp']) is not None and _parse_ts(r['timestamp']) >= cutoff_hour
    ]

    expected_last_hour = max(1, int(3600 / expected_interval_seconds)) if expected_interval_seconds else 60
    received_last_hour = len(last_hour)
    loss_percent = round(max(0.0, 1.0 - (received_last_hour / expected_last_hour)) * 100.0, 1)

    max_gap_seconds = 0.0
    prev = None
    for r in readings:
        ts = _parse_ts(r['timestamp'])
        if ts is None:
            continue
        if prev is not None:
            max_gap_seconds = max(max_gap_seconds, (ts - prev).total_seconds())
        prev = ts

    if age_seconds is None:
        state = "unknown"
    elif age_seconds <= expected_interval_seconds * 3:
        state = "online"
    elif age_seconds <= expected_interval_seconds * 10:
        state = "stale"
    else:
        state = "offline"

    return {
        "state": state,
        "last_seen": latest['timestamp'] if latest else None,
        "age_seconds": round(age_seconds, 1) if age_seconds is not None else None,
        "source": latest.get('source') if latest else None,
        "latest_water_level_m": latest.get('water_level_m') if latest else None,
        "latest_rainfall_mm": latest.get('rainfall_mm') if latest else None,
        "window_hours": window_hours,
        "readings_in_window": len(readings),
        "readings_last_hour": received_last_hour,
        "expected_last_hour": expected_last_hour,
        "loss_percent_last_hour": loss_percent,
        "max_gap_seconds": round(max_gap_seconds, 1),
        "max_gap_minutes": round(max_gap_seconds / 60.0, 1),
        "expected_interval_seconds": expected_interval_seconds,
    }


def _parse_ts(value) -> Optional[datetime]:
    """Parse a stored ISO timestamp, returning None when malformed"""
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


# ============================================================================
# ALERT CONTACTS OPERATIONS
# ============================================================================

def insert_alert_contact(name: str, phone_number: str, 
                         receive_alert: int = 1, receive_warning: int = 1, 
                         receive_critical: int = 1) -> int:
    """Insert a new alert contact"""
    with db_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alert_contacts (name, phone_number, receive_alert, receive_warning, receive_critical)
            VALUES (?, ?, ?, ?, ?)
        """, (name, phone_number, receive_alert, receive_warning, receive_critical))
        return cursor.lastrowid


def get_all_alert_contacts(active_only: bool = True) -> List[Dict]:
    """Get all alert contacts"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if active_only:
            cursor.execute("""
                SELECT * FROM alert_contacts 
                WHERE is_active = 1
                ORDER BY name
            """)
        else:
            cursor.execute("""
                SELECT * FROM alert_contacts 
                ORDER BY name
            """)
        return [dict(row) for row in cursor.fetchall()]


def get_alert_contact(contact_id: int) -> Optional[Dict]:
    """Get a single alert contact by ID, or None if not found"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alert_contacts WHERE id = ?", (contact_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_active_alert_phone_numbers(risk_level: str = None) -> List[str]:
    """Get phone numbers of active contacts for a specific risk level"""
    risk_level = (risk_level or '').strip().lower()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if risk_level == 'critical':
            cursor.execute("""
                SELECT phone_number FROM alert_contacts 
                WHERE is_active = 1 AND receive_critical = 1
            """)
        elif risk_level == 'alarm':
            cursor.execute("""
                SELECT phone_number FROM alert_contacts 
                WHERE is_active = 1 AND (receive_critical = 1 OR receive_warning = 1)
            """)
        elif risk_level == 'alert':
            cursor.execute("""
                SELECT phone_number FROM alert_contacts 
                WHERE is_active = 1 AND (receive_critical = 1 OR receive_warning = 1 OR receive_alert = 1)
            """)
        else:
            cursor.execute("""
                SELECT phone_number FROM alert_contacts 
                WHERE is_active = 1 AND receive_alert = 1
            """)
        return [row[0] for row in cursor.fetchall()]


def update_alert_contact(contact_id: int, **kwargs) -> bool:
    """Update an alert contact"""
    allowed_fields = ['name', 'phone_number', 'is_active', 'receive_alert', 'receive_warning', 'receive_critical']
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not updates:
        return False
    
    updates['updated_at'] = datetime.now().isoformat()
    
    with db_transaction() as conn:
        cursor = conn.cursor()
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [contact_id]
        cursor.execute(f"""
            UPDATE alert_contacts SET {set_clause} WHERE id = ?
        """, values)
        return cursor.rowcount > 0


def delete_alert_contact(contact_id: int) -> bool:
    """Delete an alert contact"""
    with db_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM alert_contacts WHERE id = ?", (contact_id,))
        return cursor.rowcount > 0


# ============================================================================
# SYSTEM STATUS OPERATIONS
# ============================================================================

def update_system_status(component: str, status: str, message: str = None):
    """Update system component status"""
    with db_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO system_status (timestamp, component, status, message)
            VALUES (?, ?, ?, ?)
        """, (datetime.now().isoformat(), component, status, message))


def get_system_status() -> List[Dict]:
    """Get latest status for each component"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s1.* FROM system_status s1
            INNER JOIN (
                SELECT component, MAX(timestamp) as max_ts
                FROM system_status
                GROUP BY component
            ) s2 ON s1.component = s2.component AND s1.timestamp = s2.max_ts
            ORDER BY s1.component
        """)
        return [dict(row) for row in cursor.fetchall()]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def cleanup_old_data(days: int = 30):
    """Remove data older than specified days"""
    cutoff = datetime.now() - timedelta(days=days)
    with db_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sensor_data WHERE timestamp < ?", (cutoff.isoformat(),))
        cursor.execute("DELETE FROM tidal_data WHERE timestamp < ?", (cutoff.isoformat(),))
        cursor.execute("DELETE FROM weather_data WHERE timestamp < ?", (cutoff.isoformat(),))
        cursor.execute("DELETE FROM predictions WHERE timestamp < ?", (cutoff.isoformat(),))
        cursor.execute("DELETE FROM alerts WHERE timestamp < ?", (cutoff.isoformat(),))
        cursor.execute("DELETE FROM system_status WHERE timestamp < ?", (cutoff.isoformat(),))


def get_database_stats() -> Dict:
    """Get database statistics"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        stats = {}
        for table in ['sensor_data', 'tidal_data', 'weather_data', 'predictions', 'alerts', 'system_status', 'rainfall_hourly', 'rainfall_daily']:
            # Try newer table first, fall back to legacy name for pre-migration DBs
            exists = cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            if table == 'sensor_data' and not exists:
                legacy = cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='water_levels'"
                ).fetchone()
                if legacy:
                    table = 'water_levels'
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            stats[table] = cursor.fetchone()['count']
        
        # Database file size
        if os.path.exists(DATABASE_PATH):
            stats['db_size_mb'] = round(os.path.getsize(DATABASE_PATH) / (1024 * 1024), 2)
        else:
            stats['db_size_mb'] = 0
        
        return stats


# ============================================================================
# RAINFALL OPERATIONS
# ============================================================================

def insert_rainfall_hourly(timestamp: datetime, total_tips: int, total_rainfall_mm: float) -> int:
    """Insert or update hourly rainfall aggregation"""
    with db_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO rainfall_hourly (timestamp, hour, day, month, year, total_tips, total_rainfall_mm)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(hour, day, month, year) DO UPDATE SET
                total_tips = excluded.total_tips,
                total_rainfall_mm = excluded.total_rainfall_mm
        """, (
            timestamp.isoformat(),
            timestamp.hour,
            timestamp.day,
            timestamp.month,
            timestamp.year,
            total_tips,
            total_rainfall_mm
        ))
        return cursor.lastrowid


def get_rainfall_since(hours: int = 24) -> List[Dict]:
    """Get rainfall data from the last N hours"""
    since = datetime.now() - timedelta(hours=hours)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM rainfall_hourly 
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (since.isoformat(),))
        return [dict(row) for row in cursor.fetchall()]


def get_rainfall_stats(hours: int = 24) -> Dict:
    """Get rainfall statistics for the last N hours"""
    since = datetime.now() - timedelta(hours=hours)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                SUM(total_tips) as total_tips,
                SUM(total_rainfall_mm) as total_rainfall,
                AVG(total_rainfall_mm) as avg_hourly_rainfall,
                MAX(total_rainfall_mm) as max_hourly_rainfall,
                COUNT(*) as hours_with_data
            FROM rainfall_hourly 
            WHERE timestamp >= ?
        """, (since.isoformat(),))
        row = cursor.fetchone()
        return dict(row) if row else {}


def get_rainfall_24h_total() -> float:
    """Get total rainfall in the last 24 hours"""
    stats = get_rainfall_stats(hours=24)
    return stats.get('total_rainfall', 0.0) or 0.0


# ============================================================================
# TIDAL DATA OPERATIONS
# ============================================================================

def insert_tidal_data(timestamp: datetime, tide_level_m: float) -> int:
    """Insert an hourly tide level reading"""
    with db_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tidal_data (timestamp, tide_level_m)
            VALUES (?, ?)
        """, (timestamp.isoformat(), tide_level_m))
        return cursor.lastrowid


def get_latest_tide_level() -> Optional[Dict]:
    """Get the most recent tide level reading"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM tidal_data 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        row = cursor.fetchone()
        return dict(row) if row else None


def get_tide_level_at(target: datetime) -> Optional[Dict]:
    """Get the tide level reading closest to the given time"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM tidal_data 
            ORDER BY ABS(julianday(timestamp) - julianday(?)) ASC 
            LIMIT 1
        """, (target.isoformat(),))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_tidal_data_since(hours: int = 48) -> List[Dict]:
    """Get tide level readings from the last N hours"""
    since = datetime.now() - timedelta(hours=hours)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM tidal_data 
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (since.isoformat(),))
        return [dict(row) for row in cursor.fetchall()]


def clear_tidal_data_since(start: datetime):
    """Delete tide level readings at or after the given time (replace fetch window)"""
    with db_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tidal_data WHERE timestamp >= ?", (start.isoformat(),))


# ============================================================================
# DAILY RAINFALL OPERATIONS
# ============================================================================

def upsert_rainfall_daily(date: datetime, total_tips: int, total_rainfall_mm: float) -> int:
    """Insert or update the daily rainfall aggregate for a calendar day"""
    date_str = date.strftime('%Y-%m-%d')
    with db_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO rainfall_daily (date, total_tips, total_rainfall_mm)
            VALUES (?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                total_tips = excluded.total_tips,
                total_rainfall_mm = excluded.total_rainfall_mm
        """, (date_str, total_tips, total_rainfall_mm))
        return cursor.lastrowid


def rebuild_rainfall_daily(days: int = 8) -> Dict:
    """Recompute daily rainfall totals from stored sensor readings.

    Rebuilds today plus the previous (days - 1) calendar days so the
    forecasting window (R1/R3/R7 sensor-rainfall lookup) always has fresh,
    gap-free daily aggregates even if the live receiver missed updates.
    """
    today = datetime.now().date()
    rebuilt = []
    with db_transaction() as conn:
        cursor = conn.cursor()
        for offset in range(days):
            day = today - timedelta(days=offset)
            start = datetime.combine(day, datetime.min.time())
            end = start + timedelta(days=1)
            cursor.execute("""
                SELECT COALESCE(SUM(rain_tips), 0) as tips,
                       COALESCE(SUM(rainfall_mm), 0) as rain
                FROM sensor_data
                WHERE timestamp >= ? AND timestamp < ?
            """, (start.isoformat(), end.isoformat()))
            row = cursor.fetchone()
            tips = int(row['tips'] or 0)
            rain = round(float(row['rain'] or 0.0), 3)
            cursor.execute("""
                INSERT INTO rainfall_daily (date, total_tips, total_rainfall_mm)
                VALUES (?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    total_tips = excluded.total_tips,
                    total_rainfall_mm = excluded.total_rainfall_mm
            """, (day.isoformat(), tips, rain))
            rebuilt.append({'date': day.isoformat(), 'total_tips': tips, 'total_rainfall_mm': rain})
    return {'days_rebuilt': len(rebuilt), 'window_days': days, 'daily': rebuilt}


def get_rainfall_daily_range(start: datetime, end: datetime) -> List[Dict]:
    """Get daily rainfall aggregates between two calendar days (inclusive)"""
    start_str = start.strftime('%Y-%m-%d')
    end_str = end.strftime('%Y-%m-%d')
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM rainfall_daily 
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC
        """, (start_str, end_str))
        return [dict(row) for row in cursor.fetchall()]


def get_rainfall_daily_total(date: datetime) -> float:
    """Get the total rainfall in mm for a specific calendar day (0.0 if none)"""
    date_str = date.strftime('%Y-%m-%d')
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT total_rainfall_mm FROM rainfall_daily 
            WHERE date = ?
        """, (date_str,))
        row = cursor.fetchone()
        return float(row['total_rainfall_mm']) if row else 0.0


# Initialize database on import
init_database()


# ============================================================================
# DATABASE MIGRATION
# ============================================================================

def migrate_database():
    """Migrate existing database to new schema"""
    with db_transaction() as conn:
        cursor = conn.cursor()
        
        # Rename legacy water_levels table to sensor_data (preserving data)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='water_levels'")
        legacy_exists = cursor.fetchone() is not None
        if legacy_exists:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sensor_data'")
            new_exists = cursor.fetchone() is not None
            if not new_exists:
                print("Renaming water_levels to sensor_data")
                cursor.execute("ALTER TABLE water_levels RENAME TO sensor_data")
            else:
                # init_database already created an empty sensor_data; copy rows across
                cursor.execute("INSERT INTO sensor_data (timestamp, water_level_m, raw_distance_m, raw_distance_mm, rain_tips, rainfall_mm, source) SELECT timestamp, water_level_m, raw_distance_m, raw_distance_mm, rain_tips, rainfall_mm, source FROM water_levels")
                print("Copied water_levels data into sensor_data")
            cursor.execute("DROP TABLE IF EXISTS water_levels")
            cursor.execute("DROP INDEX IF EXISTS idx_water_levels_timestamp")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp ON sensor_data(timestamp)")

        # Drop redundant created_at column where timestamp is authoritative
        for table in ('sensor_data', 'tidal_data', 'weather_data', 'predictions', 'alerts', 'system_status', 'rainfall_hourly'):
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            if 'created_at' in columns:
                print(f"Dropping created_at column from {table}")
                cursor.execute(f"ALTER TABLE {table} DROP COLUMN created_at")

        # Convert stored created_at/updated_at values to Philippines time (UTC+8) on existing DBs
        for table, defn, base_cols, time_cols in (
            ('rainfall_daily',
             "id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL UNIQUE, total_tips INTEGER DEFAULT 0, "
             "total_rainfall_mm REAL DEFAULT 0.0, "
             "created_at DATETIME DEFAULT (datetime('now', '+8 hours'))",
             ('id', 'date', 'total_tips', 'total_rainfall_mm'),
             ('created_at',)),
            ('alert_contacts',
             "id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone_number TEXT NOT NULL UNIQUE, "
             "is_active INTEGER DEFAULT 1, receive_alert INTEGER DEFAULT 1, receive_warning INTEGER DEFAULT 1, "
             "receive_critical INTEGER DEFAULT 1, "
             "created_at DATETIME DEFAULT (datetime('now', '+8 hours')), "
             "updated_at DATETIME DEFAULT (datetime('now', '+8 hours'))",
             ('id', 'name', 'phone_number', 'is_active', 'receive_alert', 'receive_warning', 'receive_critical'),
             ('created_at', 'updated_at')),
        ):
            cursor.execute(f"PRAGMA table_info({table})")
            dflt = {row[1]: row[4] for row in cursor.fetchall()}.get('created_at')
            if dflt == 'CURRENT_TIMESTAMP':
                print(f"Converting {table} timestamps to Philippines time")
                cols = ', '.join(base_cols)
                conv = ', '.join(f"datetime({c}, '+8 hours') AS {c}" for c in time_cols)
                cursor.execute(f"CREATE TABLE {table}_new ({defn})")
                cursor.execute(f"INSERT INTO {table}_new ({cols}, {', '.join(time_cols)}) SELECT {cols}, {conv} FROM {table}")
                cursor.execute(f"DROP TABLE {table}")
                cursor.execute(f"ALTER TABLE {table}_new RENAME TO {table}")

        # Ensure tidal_data and rainfall_daily exist (for DBs created pre-migration)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tidal_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                tide_level_m REAL NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rainfall_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                total_tips INTEGER DEFAULT 0,
                total_rainfall_mm REAL DEFAULT 0.0,
                created_at DATETIME DEFAULT (datetime('now', '+8 hours'))
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tidal_data_timestamp ON tidal_data(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rainfall_daily_date ON rainfall_daily(date)")

        # Check and add columns to weather_data
        cursor.execute("PRAGMA table_info(weather_data)")
        weather_columns = [row[1] for row in cursor.fetchall()]
        
        new_weather_columns = {
            'temperature_max_c': 'REAL',
            'temperature_min_c': 'REAL',
            'tide_max_m': 'REAL',
            'tide_min_m': 'REAL',
            'tide_forecast_data': 'TEXT'
        }
        
        for col, col_type in new_weather_columns.items():
            if col not in weather_columns:
                print(f"Adding column {col} to weather_data")
                cursor.execute(f"ALTER TABLE weather_data ADD COLUMN {col} {col_type}")
        
        # Check and add acknowledgement columns to alerts (pre-ack databases)
        cursor.execute("PRAGMA table_info(alerts)")
        alert_columns = [row[1] for row in cursor.fetchall()]
        new_alert_columns = {
            'acknowledged': 'INTEGER DEFAULT 0',
            'acknowledged_by': 'TEXT',
            'acknowledged_at': 'DATETIME'
        }
        for col, col_type in new_alert_columns.items():
            if col not in alert_columns:
                print(f"Adding column {col} to alerts")
                cursor.execute(f"ALTER TABLE alerts ADD COLUMN {col} {col_type}")

        # Ensure users and audit_log exist (for DBs created pre-auth)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('viewer', 'admin')),
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT (datetime('now', '+8 hours')),
                updated_at DATETIME DEFAULT (datetime('now', '+8 hours')),
                last_login DATETIME
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                actor TEXT,
                role TEXT,
                action TEXT NOT NULL,
                target TEXT,
                details TEXT,
                ip_address TEXT
            )
        """)

        # Check and add columns to predictions
        cursor.execute("PRAGMA table_info(predictions)")
        pred_columns = [row[1] for row in cursor.fetchall()]
        
        new_pred_columns = {
            'rf_propensity': 'TEXT',
            'fuzzy_inputs': 'TEXT',
            'rule_triggered': 'INTEGER',
            'risk_level_48h': 'TEXT',
            'rf_propensity_48h': 'TEXT',
            'fuzzy_inputs_48h': 'TEXT',
            'rule_triggered_48h': 'INTEGER',
            'used_fallback': 'INTEGER DEFAULT 0',
            'used_fallback_48h': 'INTEGER DEFAULT 0'
        }
        
        for col, col_type in new_pred_columns.items():
            if col not in pred_columns:
                print(f"Adding column {col} to predictions")
                cursor.execute(f"ALTER TABLE predictions ADD COLUMN {col} {col_type}")
        
        print("Database migration completed")