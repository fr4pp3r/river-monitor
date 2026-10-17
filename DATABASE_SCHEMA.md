# Database Schema & Migrations — River Monitor

Database file: `data/river_monitor.db` (SQLite, WAL mode). Schema reflects the live, migrated database.

## Full Schema (DDL)

### sensor_data
```sql
CREATE TABLE sensor_data (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       DATETIME NOT NULL,
    water_level_m   REAL NOT NULL,
    raw_distance_m  REAL NOT NULL,
    raw_distance_mm INTEGER,
    rain_tips       INTEGER DEFAULT 0,
    rainfall_mm     REAL,
    source          TEXT NOT NULL CHECK (source IN ('lora', 'sms'))
);
CREATE INDEX idx_sensor_data_timestamp ON sensor_data(timestamp);
```

### tidal_data
```sql
CREATE TABLE tidal_data (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp     DATETIME NOT NULL,
    tide_level_m  REAL NOT NULL
);
CREATE INDEX idx_tidal_data_timestamp ON tidal_data(timestamp);
```

### rainfall_daily
```sql
CREATE TABLE rainfall_daily (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    date              TEXT NOT NULL UNIQUE,
    total_tips        INTEGER DEFAULT 0,
    total_rainfall_mm REAL DEFAULT 0.0,
    created_at        DATETIME DEFAULT (datetime('now', '+8 hours'))
);
CREATE INDEX idx_rainfall_daily_date ON rainfall_daily(date);
```

### rainfall_hourly
```sql
CREATE TABLE rainfall_hourly (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp        DATETIME NOT NULL,
    hour             INTEGER NOT NULL,
    day              INTEGER NOT NULL,
    month            INTEGER NOT NULL,
    year             INTEGER NOT NULL,
    total_tips       INTEGER DEFAULT 0,
    total_rainfall_mm REAL DEFAULT 0.0,
    UNIQUE(hour, day, month, year)
);
CREATE INDEX idx_rainfall_hourly_timestamp ON rainfall_hourly(timestamp);
```

### weather_data
```sql
CREATE TABLE weather_data (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp          DATETIME NOT NULL,
    precipitation_mm   REAL,
    temperature_max_c  REAL,
    temperature_min_c  REAL,
    tide_max_m         REAL,
    tide_min_m         REAL,
    pressure_hpa       REAL,
    temperature_c      REAL,
    humidity_percent   REAL,
    wind_speed_ms      REAL,
    wind_direction_deg REAL,
    forecast_data      TEXT,  -- JSON string of forecast
    tide_forecast_data TEXT   -- JSON string of tide forecast
);
CREATE INDEX idx_weather_data_timestamp ON weather_data(timestamp);
```

### predictions
```sql
CREATE TABLE predictions (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp             DATETIME NOT NULL,
    current_level_m       REAL NOT NULL,
    risk_level            TEXT NOT NULL,
    risk_level_48h        TEXT,
    rf_propensity         TEXT,  -- 'Low', 'Medium', 'High'
    rf_propensity_48h     TEXT,
    fuzzy_inputs          TEXT,  -- JSON of WL, RoR, FRain, Tide, RF
    fuzzy_inputs_48h      TEXT,
    rule_triggered        INTEGER,  -- Which rule fired (1-20)
    rule_triggered_48h    INTEGER,
    used_fallback         INTEGER DEFAULT 0,  -- 1 if fallback scoring used
    used_fallback_48h     INTEGER DEFAULT 0,
    forecast_data         TEXT NOT NULL,  -- JSON array of 7 daily predictions
    model_version         TEXT
);
CREATE INDEX idx_predictions_timestamp ON predictions(timestamp);
```

### alerts
```sql
CREATE TABLE alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       DATETIME NOT NULL,
    risk_level      TEXT NOT NULL,
    water_level_m   REAL NOT NULL,
    message         TEXT NOT NULL,
    sent_to         TEXT,  -- Comma-separated phone numbers
    status          TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
    acknowledged    INTEGER DEFAULT 0,
    acknowledged_by TEXT,
    acknowledged_at DATETIME
);
CREATE INDEX idx_alerts_timestamp ON alerts(timestamp);
```

### users
```sql
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('viewer', 'admin')),
    is_active     INTEGER DEFAULT 1,
    created_at    DATETIME DEFAULT (datetime('now', '+8 hours')),
    updated_at    DATETIME DEFAULT (datetime('now', '+8 hours')),
    last_login    DATETIME
);
```

### audit_log
```sql
CREATE TABLE audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   DATETIME NOT NULL,
    actor       TEXT,
    role        TEXT,
    action      TEXT NOT NULL,
    target      TEXT,
    details     TEXT,
    ip_address  TEXT
);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);
```

### alert_contacts
```sql
CREATE TABLE alert_contacts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT NOT NULL,
    phone_number     TEXT NOT NULL UNIQUE,
    is_active        INTEGER DEFAULT 1,
    receive_alert    INTEGER DEFAULT 1,
    receive_warning  INTEGER DEFAULT 1,
    receive_critical INTEGER DEFAULT 1,
    created_at       DATETIME DEFAULT (datetime('now', '+8 hours')),
    updated_at       DATETIME DEFAULT (datetime('now', '+8 hours'))
);
```

### system_status
```sql
CREATE TABLE system_status (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp  DATETIME NOT NULL,
    component  TEXT NOT NULL,
    status     TEXT NOT NULL CHECK (status IN ('ok', 'warning', 'error')),
    message    TEXT
);
CREATE INDEX idx_system_status_timestamp ON system_status(timestamp);
```

> Internal SQLite table `sqlite_sequence` (AUTOINCREMENT bookkeeping) is also present.

---

## Migration History

Migrations are applied by `migrate_database()` in `src/data/database.py` (invoked via `migrate_db.py`). `init_database()` first ensures all tables exist with the current schema (CREATE TABLE IF NOT EXISTS), then `migrate_database()` upgrades older databases.

### 1. Legacy table rename: `water_levels` → `sensor_data`
- If `water_levels` exists and `sensor_data` does not, rename via `ALTER TABLE water_levels RENAME TO sensor_data`.
- If both exist, copy rows from `water_levels` into `sensor_data`, then drop `water_levels` and its index `idx_water_levels_timestamp`.
- Recreate `idx_sensor_data_timestamp`.

### 2. Drop redundant `created_at` columns
- For tables `sensor_data`, `tidal_data`, `weather_data`, `predictions`, `alerts`, `system_status`, `rainfall_hourly`: if a `created_at` column exists, drop it (`ALTER TABLE ... DROP COLUMN created_at`), since `timestamp` is authoritative.

### 3. Philippines-time (UTC+8) conversion for `rainfall_daily` and `alert_contacts`
- If `created_at` default is `CURRENT_TIMESTAMP` (UTC) on `rainfall_daily` / `alert_contacts`, rebuild the table:
  - Create `<table>_new` with `created_at`/`updated_at` default `datetime('now', '+8 hours')`.
  - Copy rows, converting `created_at`/`updated_at` via `datetime(col, '+8 hours')`.
  - Drop old table, rename new one.
- Applies to `rainfall_daily` (`created_at`) and `alert_contacts` (`created_at`, `updated_at`).

### 4. Ensure newer tables exist on pre-migration DBs
- `CREATE TABLE IF NOT EXISTS tidal_data (...)`.
- `CREATE TABLE IF NOT EXISTS rainfall_daily (...)`.
- Recreate `idx_tidal_data_timestamp`, `idx_rainfall_daily_date`.

### 5. `weather_data` column additions
- Added if missing: `temperature_max_c`, `temperature_min_c`, `tide_max_m`, `tide_min_m`, `tide_forecast_data` (REAL/TEXT).

### 6. `alerts` acknowledgement columns
- Added if missing: `acknowledged` (INTEGER DEFAULT 0), `acknowledged_by` (TEXT), `acknowledged_at` (DATETIME).

### 7. Ensure `users` and `audit_log` exist (auth feature)
- `CREATE TABLE IF NOT EXISTS users (...)`.
- `CREATE TABLE IF NOT EXISTS audit_log (...)`.

### 8. `predictions` column additions (dual-horizon + fuzzy)
- Added if missing: `rf_propensity`, `fuzzy_inputs`, `rule_triggered`, `risk_level_48h`, `rf_propensity_48h`, `fuzzy_inputs_48h`, `rule_triggered_48h`, `used_fallback`, `used_fallback_48h`.

### Table creation defaults (init_database)
- All tables created with `CREATE TABLE IF NOT EXISTS` using the current schema above, including CHECK constraints and UNIQUE constraints.
- Indexes created with `CREATE INDEX IF NOT EXISTS`.

### Notes
- No foreign-key constraints are declared; relationships are logical (see `DATABASE_ERD.md`).
- Timestamps are stored as ISO-8601 strings; many default to Philippines time (`+8 hours`).
- `source` on `sensor_data` restricted to `'lora'` or `'sms'`.
- `alerts.status` restricted to `'pending'`, `'sent'`, `'failed'`.
- `system_status.status` restricted to `'ok'`, `'warning'`, `'error'`.
- `users.role` restricted to `'viewer'`, `'admin'`.
