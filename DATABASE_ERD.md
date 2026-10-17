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
