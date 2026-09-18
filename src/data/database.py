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
                source TEXT NOT NULL CHECK (source IN ('lora', 'sms')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Hourly tide level readings (from Open-Meteo marine API)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tidal_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                tide_level_m REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Daily rainfall totals (one row per calendar day, 'YYYY-MM-DD')
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rainfall_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                total_tips INTEGER DEFAULT 0,
                total_rainfall_mm REAL DEFAULT 0.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
                tide_forecast_data TEXT,  -- JSON string of tide forecast
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
                rule_triggered INTEGER,  -- Which rule fired (1-15)
                rule_triggered_48h INTEGER,  -- Which rule fired (1-15)
                forecast_data TEXT NOT NULL,  -- JSON array of 7 daily predictions
                model_version TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # System status table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                component TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('ok', 'warning', 'error')),
                message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
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


def get_latest_weather() -> Optional[Dict]:
    """Get the most recent weather data"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM weather_data 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        row = cursor.fetchone()
        return dict(row) if row else None


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
                      fuzzy_inputs_48h: dict = None, rule_triggered_48h: int = None) -> int:
    """Insert a prediction"""
    import json
    with db_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO predictions (timestamp, current_level_m, risk_level, risk_level_48h,
                                     rf_propensity, rf_propensity_48h, fuzzy_inputs, fuzzy_inputs_48h,
                                     rule_triggered, rule_triggered_48h, forecast_data, model_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp.isoformat(), current_level_m, risk_level, risk_level_48h,
              rf_propensity, rf_propensity_48h,
              json.dumps(fuzzy_inputs) if fuzzy_inputs else None,
              json.dumps(fuzzy_inputs_48h) if fuzzy_inputs_48h else None,
              rule_triggered, rule_triggered_48h,
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
                cursor.execute("INSERT INTO sensor_data (timestamp, water_level_m, raw_distance_m, raw_distance_mm, rain_tips, rainfall_mm, source, created_at) SELECT timestamp, water_level_m, raw_distance_m, raw_distance_mm, rain_tips, rainfall_mm, source, created_at FROM water_levels")
                print("Copied water_levels data into sensor_data")
            cursor.execute("DROP TABLE IF EXISTS water_levels")
            cursor.execute("DROP INDEX IF EXISTS idx_water_levels_timestamp")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp ON sensor_data(timestamp)")

        # Ensure tidal_data and rainfall_daily exist (for DBs created pre-migration)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tidal_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                tide_level_m REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rainfall_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                total_tips INTEGER DEFAULT 0,
                total_rainfall_mm REAL DEFAULT 0.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
            'rule_triggered_48h': 'INTEGER'
        }
        
        for col, col_type in new_pred_columns.items():
            if col not in pred_columns:
                print(f"Adding column {col} to predictions")
                cursor.execute(f"ALTER TABLE predictions ADD COLUMN {col} {col_type}")
        
        print("Database migration completed")