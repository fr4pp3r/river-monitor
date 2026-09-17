"""
Configuration file for River Monitor System
Adjust these values according to your hardware setup and requirements
"""

# ============================================================================
# MODULE ENABLE/DISABLE FLAGS
# ============================================================================

# Set to False to disable hardware modules (useful for development/testing)
LORA_ENABLED = True    # Enable/disable LoRa receiver module
# SMS is send-only: the sensor node has no SMS module, so the A7608e-H is
# used solely to deliver alert messages to configured phone numbers.
SMS_ENABLED = False    # Enable/disable SMS alert sending

# ============================================================================
# HARDWARE CONFIGURATION
# ============================================================================

# LoRa Module (RFM95W) - SPI Configuration
LORA_SPI_PORT = 0
LORA_CE_PIN = 5      # Chip Enable GPIO pin
LORA_CS_PIN = 8       # Chip Select GPIO pin  
LORA_RESET_PIN = 22   # Reset GPIO pin
LORA_FREQUENCY = 915.0 # MHz - 915MHz band
LORA_BANDWIDTH = 125  # kHz
# Spreading factor must match the sensor node (Feather RadioHead RH_RF95 default = 7).
# SF12 and SF7 are incompatible - an SF7 node cannot be heard by an SF12 receiver.
LORA_SPREADING_FACTOR = 7
LORA_CODING_RATE = 5

# SMS Module (A7608e-H) - UART Configuration
SMS_UART_PORT = "/dev/ttyS0"  # Default UART port on Raspberry Pi
SMS_BAUD_RATE = 115200        # Baud rate for A7608e-H
SMS_TIMEOUT = 5               # Timeout in seconds for SMS operations

# Sensor Configuration
SENSOR_MAX_DISTANCE = 2.5   # Maximum distance sensor can measure (meters)
SENSOR_MAX_DISTANCE_MM = 2500  # Maximum distance in millimeters

# Rain Gauge Configuration
RAIN_BUCKET_TIP_MM = 0.2  # Rainfall per tip in mm (adjust based on your bucket calibration)

# ============================================================================
# RISK THRESHOLDS (PAGASA Compliant)
# ============================================================================

# Risk levels based on percentage of critical level
RISK_THRESHOLDS = {
    "normal": 0.0,
    "alert": 0.40,    # 40% of critical level
    "alarm": 0.60,    # 60% of critical level
    "critical": 1.0   # 100% of critical level
}

# Critical water level (meters) - Adjust after hydrological survey
# This is the water level at which risk is considered 100%
CRITICAL_LEVEL_M = 2.0

# Receding condition: Water level must drop for this many hours to be considered receding
RECEDING_HOURS = 2

# ============================================================================
# WEATHER API CONFIGURATION (Open-Meteo)
# ============================================================================

# Open-Meteo API (free, no API key required)
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
MARINE_API_URL = "https://marine-api.open-meteo.com/v1/marine"

# Location coordinates (default: Manila)
WEATHER_LATITUDE = 9.299495315028961
WEATHER_LONGITUDE = 118.43788786664786

# Weather parameters
WEATHER_DAILY_PARAMS = "temperature_2m_max,temperature_2m_min,precipitation_sum"
# Hourly params used to populate the dashboard's current temp / pressure / humidity
WEATHER_HOURLY_PARAMS = "temperature_2m,relative_humidity_2m,surface_pressure,precipitation"
MARINE_HOURLY_PARAMS = "sea_level_height_msl"
WEATHER_TIMEZONE = "auto"
WEATHER_FORECAST_DAYS = 7

# Cache settings
WEATHER_CACHE_EXPIRY = 21600  # 6 hours in seconds

# ============================================================================
# SMS ALERT CONFIGURATION
# ============================================================================

# Phone numbers to receive SMS alerts (format: ["+639123456789", "+639876543210"])
ALERT_PHONE_NUMBERS = ["+639940176150"]  # REPLACE WITH ACTUAL NUMBERS

# Risk levels that trigger SMS alerts
SMS_ALERT_RISK_LEVELS = ["alarm", "critical"]

# SMS message template
SMS_ALERT_TEMPLATE = "[RIVER ALERT] Risk: {risk_level} | Water: {water_level:.2f}m | Forecast: {forecast_change:+.2f}m in 1d"

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# SQLite database path
DATABASE_PATH = "data/river_monitor.db"

# ============================================================================
# WEB DASHBOARD CONFIGURATION
# ============================================================================

# FastAPI server configuration
DASHBOARD_HOST = "0.0.0.0"  # Listen on all interfaces
DASHBOARD_PORT = 8000       # Port for the web dashboard

# Auto-refresh settings for frontend
AUTO_REFRESH_SECONDS = 30   # Dashboard auto-refresh interval

# ============================================================================
# DATA COLLECTION CONFIGURATION
# ============================================================================

# Water level data collection interval (seconds)
WATER_LEVEL_INTERVAL = 60  # 1 minute

# Maximum time without LoRa data before the receiver logs a stale-data warning (seconds)
LORA_FALLBACK_TIMEOUT = 300  # 5 minutes (5 missed intervals at 1 min each)

# Weather data fetch interval (seconds)
WEATHER_FETCH_INTERVAL = 21600  # 6 hours

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

# Path to trained model
MODEL_PATH = "data/models/rf_model.pkl"

# Model training parameters (for train.py)
MODEL_N_ESTIMATORS = 100
MODEL_MAX_DEPTH = 10
MODEL_RANDOM_STATE = 42
MODEL_TEST_SIZE = 0.2

# Forecast parameters
FORECAST_DAYS = 7  # Predict next 7 days

# RF Model features (8 features for daily model)
RF_FEATURES = ['R1', 'R3', 'R7', 'rainy_days', 'TMAX', 'TMIN', 'TideMax', 'TideMin']

# RF Model target classes
RF_CLASSES = {0: 'Low', 1: 'Medium', 2: 'High'}

# ============================================================================
# FUZZY LOGIC CONFIGURATION
# ============================================================================

# Fuzzy Logic Membership Function Thresholds

# Water Level (mm) - from sensor
WL_THRESHOLDS = {
    'low_max': 610,
    'medium_min': 610, 'medium_max': 1220,
    'high_min': 1220, 'high_max': 1830,
    'very_high_min': 1830
}

# Forecast Rain (mm/day) - from Open-Meteo precipitation_sum
FRAIN_THRESHOLDS = {
    'none_max': 5,
    'light_min': 5, 'light_max': 15,
    'moderate_min': 15, 'moderate_max': 30,
    'heavy_min': 30
}

# Rate of Rise (mm/hour) - computed from hourly resampled water level data
ROR_THRESHOLDS = {
    'negative_max': -0.5,
    'near_zero_min': -0.5, 'near_zero_max': 0.5,
    'moderate_min': 0.5, 'moderate_max': 4.0,
    'rapid_min': 4.0
}

# Tide Level (meters) - from Open-Meteo marine API
TIDE_THRESHOLDS = {
    'low_max': 0.5,
    'mid_min': 0.5, 'mid_max': 1.0,
    'high_min': 1.0, 'high_max': 1.5,
    'extreme_min': 1.5
}

# RF Propensity (crisp: 0=Low, 1=Medium, 2=High)
RF_PROPENSITY_MAP = {0: 'Low', 1: 'Medium', 2: 'High'}

# Fuzzy Output Risk Levels
RISK_LEVELS = ['Receding', 'Alert', 'Alarm', 'Critical']

# ============================================================================
# RoR COMPUTATION CONFIGURATION
# ============================================================================

# Rate of Rise computation resampling window (hours)
ROR_RESAMPLE_HOURS = 1  # Water levels resampled to 1-hour intervals

# ============================================================================
# JSON OVERRIDE LOADING
# ============================================================================
# Apply any user-saved overrides from config.json at import time.
try:
    from src.config_manager import load_config_from_json
    load_config_from_json()
except Exception:
    pass  # Gracefully ignore if config_manager has issues