# Database ERD — River Monitor

SQLite database (`data/river_monitor.db`). No foreign-key constraints are declared; relationships below are logical (derived from how the application joins/uses the tables).

```mermaid
erDiagram
    sensor_data {
        INTEGER id PK
        DATETIME timestamp
        REAL water_level_m
        REAL raw_distance_m
        INTEGER raw_distance_mm
        INTEGER rain_tips
        REAL rainfall_mm
        TEXT source
    }

    tidal_data {
        INTEGER id PK
        DATETIME timestamp
        REAL tide_level_m
    }

    rainfall_daily {
        INTEGER id PK
        TEXT date UK
        INTEGER total_tips
        REAL total_rainfall_mm
        DATETIME created_at
    }

    rainfall_hourly {
        INTEGER id PK
        DATETIME timestamp
        INTEGER hour
        INTEGER day
        INTEGER month
        INTEGER year
        INTEGER total_tips
        REAL total_rainfall_mm
    }

    weather_data {
        INTEGER id PK
        DATETIME timestamp
        REAL precipitation_mm
        REAL temperature_max_c
        REAL temperature_min_c
        REAL tide_max_m
        REAL tide_min_m
        REAL pressure_hpa
        REAL temperature_c
        REAL humidity_percent
        REAL wind_speed_ms
        REAL wind_direction_deg
        TEXT forecast_data
        TEXT tide_forecast_data
    }

    predictions {
        INTEGER id PK
        DATETIME timestamp
        REAL current_level_m
        TEXT risk_level
        TEXT risk_level_48h
        TEXT rf_propensity
        TEXT rf_propensity_48h
        TEXT fuzzy_inputs
        TEXT fuzzy_inputs_48h
        INTEGER rule_triggered
        INTEGER rule_triggered_48h
        INTEGER used_fallback
        INTEGER used_fallback_48h
        TEXT forecast_data
        TEXT model_version
    }

    alerts {
        INTEGER id PK
        DATETIME timestamp
        TEXT risk_level
        REAL water_level_m
        TEXT message
        TEXT sent_to
        TEXT status
        INTEGER acknowledged
        TEXT acknowledged_by
        DATETIME acknowledged_at
    }

    users {
        INTEGER id PK
        TEXT username UK
        TEXT password_hash
        TEXT role
        INTEGER is_active
        DATETIME created_at
        DATETIME updated_at
        DATETIME last_login
    }

    audit_log {
        INTEGER id PK
        DATETIME timestamp
        TEXT actor
        TEXT role
        TEXT action
        TEXT target
        TEXT details
        TEXT ip_address
    }

    alert_contacts {
        INTEGER id PK
        TEXT name
        TEXT phone_number UK
        INTEGER is_active
        INTEGER receive_alert
        INTEGER receive_warning
        INTEGER receive_critical
        DATETIME created_at
        DATETIME updated_at
    }

    system_status {
        INTEGER id PK
        DATETIME timestamp
        TEXT component
        TEXT status
        TEXT message
    }

    %% Logical relationships
    sensor_data ||--o{ rainfall_hourly : "aggregated into"
    sensor_data ||--o{ rainfall_daily : "aggregated into"
    sensor_data ||--o{ predictions : "current_level_m from latest reading"
    sensor_data ||--o{ alerts : "water_level_m snapshot"
    predictions ||--o{ alerts : "triggers on Alarm/Critical"
    users ||--o{ audit_log : "actor"
    users ||--o{ alerts : "acknowledged_by"
    alert_contacts ||--o{ alerts : "sent_to (phone numbers)"
    weather_data ||--o{ predictions : "features (rain, tide, temp)"
    tidal_data ||--o{ predictions : "tide level input"
```

## Table groups
- **Sensor/ingestion**: `sensor_data`, `tidal_data`, `rainfall_hourly`, `rainfall_daily`
- **Weather**: `weather_data`
- **AI output**: `predictions`
- **Alerting**: `alerts`, `alert_contacts`
- **Auth/audit**: `users`, `audit_log`
- **Ops**: `system_status`

## Description and Discussion

### Description
The ERD models the data layer of the River Monitor system, a SQLite database on a Raspberry Pi 5. It contains 11 entities grouped into six functional domains: sensor ingestion, weather/tide, AI prediction output, alerting, authentication/audit, and operations. Each entity is identified by a surrogate integer primary key (`id`), and natural keys such as `username`, `phone_number`, and `date` are enforced as `UNIQUE`. There are no declared foreign keys; integrity is maintained in application code, which keeps the schema simple and migration-friendly on SQLite.

### Discussion
- **Ingestion vs. aggregation split**: Raw 1-minute readings live in `sensor_data`, while `rainfall_hourly` and `rainfall_daily` are derived aggregates. This separates high-frequency capture from the coarser time windows the AI pipeline needs (R1/R3/R7, rain days), avoiding repeated full-table scans.
- **Dual-horizon prediction in one row**: `predictions` stores both 24 h and 48 h results (risk level, RF propensity, fuzzy inputs, triggered rule, fallback flag) in a single row keyed by `timestamp`. This keeps the two horizons aligned to one prediction event and simplifies "latest prediction" lookups.
- **Alerting lifecycle**: `alerts` captures the full lifecycle (pending → sent/failed) plus acknowledgement (`acknowledged`, `acknowledged_by`, `acknowledged_at`), while `alert_contacts` holds recipient preferences (`receive_alert/warning/critical`). `alerts.sent_to` stores the resolved phone list as text, decoupling delivery records from contact changes.
- **Auth and accountability**: `users` supports two roles (viewer/admin) with password hashes; `audit_log` records mutating actions with actor, role, target, and IP. This provides a minimal but complete accountability trail for a LAN dashboard.
- **Operational observability**: `system_status` keeps the latest status per component (LoRa, SMS, weather, model) for the dashboard's health view, and `weather_data`/`tidal_data` cache Open-Meteo responses so the AI pipeline and dashboard can run offline within the cache window.
- **Trade-offs**: Skipping foreign keys eases SQLite migrations and keeps the schema portable, at the cost of referential checks being handled in Python. JSON columns (`forecast_data`, `fuzzy_inputs`) keep flexible, versioned payloads without schema churn. Overall, the ERD favors read/write simplicity and operational resilience over strict relational normalization.
