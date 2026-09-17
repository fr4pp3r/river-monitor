"""
JSON-based configuration manager for River Monitor.
Loads overrides from config.json at the project root.
Falls back to config.py defaults when JSON is missing or a key is absent.
"""

import json
import os
import threading

_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config.json",
)
_lock = threading.Lock()

# Flat mapping: JSON key (snake_case) -> config module attribute (UPPER_CASE)
_FLAT_SCHEMA = {
    "lora_enabled": "LORA_ENABLED",
    "sms_enabled": "SMS_ENABLED",
    "lora_spi_port": "LORA_SPI_PORT",
    "lora_ce_pin": "LORA_CE_PIN",
    "lora_cs_pin": "LORA_CS_PIN",
    "lora_reset_pin": "LORA_RESET_PIN",
    "lora_frequency": "LORA_FREQUENCY",
    "lora_bandwidth": "LORA_BANDWIDTH",
    "lora_spreading_factor": "LORA_SPREADING_FACTOR",
    "lora_coding_rate": "LORA_CODING_RATE",
    "sms_uart_port": "SMS_UART_PORT",
    "sms_baud_rate": "SMS_BAUD_RATE",
    "sms_timeout": "SMS_TIMEOUT",
    "sensor_max_distance": "SENSOR_MAX_DISTANCE",
    "rain_bucket_tip_mm": "RAIN_BUCKET_TIP_MM",
    "critical_level_m": "CRITICAL_LEVEL_M",
    "receding_hours": "RECEDING_HOURS",
    "weather_latitude": "WEATHER_LATITUDE",
    "weather_longitude": "WEATHER_LONGITUDE",
    "weather_cache_expiry": "WEATHER_CACHE_EXPIRY",
    "weather_forecast_days": "WEATHER_FORECAST_DAYS",
    "weather_timezone": "WEATHER_TIMEZONE",
    "dashboard_host": "DASHBOARD_HOST",
    "dashboard_port": "DASHBOARD_PORT",
    "auto_refresh_seconds": "AUTO_REFRESH_SECONDS",
    "water_level_interval": "WATER_LEVEL_INTERVAL",
    "lora_fallback_timeout": "LORA_FALLBACK_TIMEOUT",
    "weather_fetch_interval": "WEATHER_FETCH_INTERVAL",
    "model_path": "MODEL_PATH",
    "forecast_days": "FORECAST_DAYS",
    "ror_resample_hours": "ROR_RESAMPLE_HOURS",
}

# Complex nested settings: JSON key -> config module attribute
_NESTED_SCHEMA = {
    "risk_thresholds": "RISK_THRESHOLDS",
    "wl_thresholds": "WL_THRESHOLDS",
    "frain_thresholds": "FRAIN_THRESHOLDS",
    "ror_thresholds": "ROR_THRESHOLDS",
    "tide_thresholds": "TIDE_THRESHOLDS",
    "sms_alert_risk_levels": "SMS_ALERT_RISK_LEVELS",
}

# Type expectations for validation
_TYPE_MAP = {
    "lora_enabled": bool,
    "sms_enabled": bool,
    "lora_spi_port": int,
    "lora_ce_pin": int,
    "lora_cs_pin": int,
    "lora_reset_pin": int,
    "lora_frequency": (int, float),
    "lora_bandwidth": int,
    "lora_spreading_factor": int,
    "lora_coding_rate": int,
    "sms_baud_rate": int,
    "sms_timeout": (int, float),
    "sensor_max_distance": (int, float),
    "rain_bucket_tip_mm": (int, float),
    "critical_level_m": (int, float),
    "receding_hours": (int, float),
    "weather_latitude": (int, float),
    "weather_longitude": (int, float),
    "weather_cache_expiry": int,
    "weather_forecast_days": int,
    "dashboard_port": int,
    "auto_refresh_seconds": (int, float),
    "water_level_interval": (int, float),
    "lora_fallback_timeout": (int, float),
    "weather_fetch_interval": (int, float),
    "forecast_days": int,
    "ror_resample_hours": (int, float),
}


def _read_json():
    """Read config.json from disk. Returns dict or None."""
    if not os.path.isfile(_CONFIG_PATH):
        return None
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(data):
    """Write dict to config.json. Returns True on success."""
    try:
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def load_config_from_json():
    """Read config.json and apply overrides to src.config module globals."""
    import src.config as cfg

    data = _read_json()
    if data is None:
        return

    with _lock:
        # Apply flat overrides
        for json_key, attr_name in _FLAT_SCHEMA.items():
            if json_key in data:
                setattr(cfg, attr_name, data[json_key])

        # Apply nested overrides (update in-place, don't replace)
        for json_key, attr_name in _NESTED_SCHEMA.items():
            if json_key in data:
                current = getattr(cfg, attr_name, None)
                if isinstance(current, dict) and isinstance(data[json_key], dict):
                    current.update(data[json_key])
                else:
                    setattr(cfg, attr_name, data[json_key])


def save_config_to_json():
    """Snapshot current src.config values into config.json."""
    import src.config as cfg

    data = {}

    with _lock:
        for json_key, attr_name in _FLAT_SCHEMA.items():
            data[json_key] = getattr(cfg, attr_name, None)

        for json_key, attr_name in _NESTED_SCHEMA.items():
            val = getattr(cfg, attr_name, None)
            # Make a shallow copy of dicts so the file is independent
            if isinstance(val, dict):
                data[json_key] = dict(val)
            else:
                data[json_key] = val

    return _write_json(data)


def get_config_dict():
    """Return all current config values as a JSON-serializable dict."""
    import src.config as cfg

    data = {}

    for json_key, attr_name in _FLAT_SCHEMA.items():
        data[json_key] = getattr(cfg, attr_name, None)

    for json_key, attr_name in _NESTED_SCHEMA.items():
        val = getattr(cfg, attr_name, None)
        if isinstance(val, dict):
            data[json_key] = dict(val)
        else:
            data[json_key] = val

    return data


def apply_config_dict(data):
    """
    Apply a dict of config values to module globals and persist to JSON.

    Returns (True, None) on success or (False, error_message) on failure.
    """
    import src.config as cfg

    # --- Validate ---
    for json_key, expected in _TYPE_MAP.items():
        if json_key in data:
            val = data[json_key]
            if val is not None and not isinstance(val, expected):
                return False, f"{json_key}: expected {expected}, got {type(val).__name__}"

    # Range checks
    port = data.get("dashboard_port")
    if port is not None and (not isinstance(port, int) or port < 1 or port > 65535):
        return False, "dashboard_port must be between 1 and 65535"

    lat = data.get("weather_latitude")
    if lat is not None and (lat < -90 or lat > 90):
        return False, "weather_latitude must be between -90 and 90"

    lon = data.get("weather_longitude")
    if lon is not None and (lon < -180 or lon > 180):
        return False, "weather_longitude must be between -180 and 180"

    # --- Apply ---
    with _lock:
        for json_key, attr_name in _FLAT_SCHEMA.items():
            if json_key in data:
                setattr(cfg, attr_name, data[json_key])

        for json_key, attr_name in _NESTED_SCHEMA.items():
            if json_key in data:
                current = getattr(cfg, attr_name, None)
                if isinstance(current, dict) and isinstance(data[json_key], dict):
                    current.update(data[json_key])
                else:
                    setattr(cfg, attr_name, data[json_key])

    # --- Persist ---
    if not save_config_to_json():
        return False, "Failed to write config.json"

    return True, None


def reset_to_defaults():
    """
    Delete config.json (if it exists) and reload the hardcoded defaults.
    Returns (True, None) on success.
    """
    import importlib
    import src.config as cfg

    with _lock:
        # Remove the file
        if os.path.isfile(_CONFIG_PATH):
            try:
                os.remove(_CONFIG_PATH)
            except OSError as e:
                return False, f"Failed to delete config.json: {e}"

        # Reload the module to restore defaults
        importlib.reload(cfg)

    return True, None
