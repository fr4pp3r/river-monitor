from __future__ import annotations
from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_bool(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    s = str(v).strip().lower()
    return s in ("true", "1", "yes", "on", "t", "y")


def _parse_list(v):
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, tuple):
        return [str(x).strip() for x in v if str(x).strip()]
    if v is None:
        return []
    s = str(v)
    return [x.strip() for x in s.split(",") if x.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "River Monitor"
    app_env: str = "development"
    app_debug: bool = False
    timezone: str = "Asia/Manila"

    # Database
    database_path: str = "data/river_monitor.db"

    # Dashboard
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8000
    auto_refresh_seconds: int = 30

    # Authentication
    auth_enabled: bool = True
    secret_key: str = "change-me-in-production-river-monitor"
    session_max_age_seconds: int = 43200
    admin_username: str = "admin"
    admin_password: str = "admin"

    # Hardware
    lora_enabled: bool = True
    sms_enabled: bool = False

    # LoRa
    lora_spi_port: int = 0
    lora_ce_pin: int = 5
    lora_cs_pin: int = 8
    lora_reset_pin: int = 22
    lora_frequency: float = 915.0
    lora_bandwidth: int = 125
    lora_spreading_factor: int = 7
    lora_coding_rate: int = 5

    # SMS
    sms_uart_port: str = "/dev/ttyUSB2"
    sms_baud_rate: int = 115200
    sms_timeout: float = 5

    # Alerts
    alert_phone_numbers: Union[str, List[str]] = ["+639940176150"]
    sms_alert_risk_levels: Union[str, List[str]] = ["alarm", "critical"]
    sms_alert_cooldown_minutes: int = 30

    # Weather
    weather_latitude: float = 9.299495315028961
    weather_longitude: float = 118.43788786664786
    weather_forecast_days: int = 7
    weather_cache_expiry: int = 21600
    weather_timezone: str = "auto"

    # Risk
    critical_level_m: float = 2.0
    receding_hours: int = 2
    rain_day_threshold_mm: float = 2.0

    # WL thresholds
    wl_low_max: float = 610
    wl_medium_min: float = 610
    wl_medium_max: float = 1220
    wl_high_min: float = 1220
    wl_high_max: float = 1830
    wl_very_high_min: float = 1830

    # FRain
    frain_none_max: float = 5
    frain_light_min: float = 5
    frain_light_max: float = 15
    frain_moderate_min: float = 15
    frain_moderate_max: float = 30
    frain_heavy_min: float = 30

    # ROR
    ror_negative_max: float = -0.5
    ror_near_zero_min: float = -0.5
    ror_near_zero_max: float = 0.5
    ror_moderate_min: float = 0.5
    ror_moderate_max: float = 4.0
    ror_rapid_min: float = 4.0

    # Tide
    tide_low_max: float = 0.5
    tide_mid_min: float = 0.5
    tide_mid_max: float = 1.0
    tide_high_min: float = 1.0
    tide_high_max: float = 1.5
    tide_extreme_min: float = 1.5

    @field_validator("lora_enabled", "sms_enabled", "app_debug", mode="before")
    @classmethod
    def _v_bool(cls, v):
        return _parse_bool(v)

    @field_validator("alert_phone_numbers", "sms_alert_risk_levels", mode="before")
    @classmethod
    def _v_list(cls, v):
        return _parse_list(v)

    @property
    def alert_phone_numbers_list(self):
        if isinstance(self.alert_phone_numbers, list):
            return self.alert_phone_numbers
        return _parse_list(self.alert_phone_numbers)

    @property
    def sms_alert_risk_levels_list(self):
        if isinstance(self.sms_alert_risk_levels, list):
            return self.sms_alert_risk_levels
        return _parse_list(self.sms_alert_risk_levels)

    @property
    def wl_thresholds(self):
        return {
            "low_max": self.wl_low_max,
            "medium_min": self.wl_medium_min,
            "medium_max": self.wl_medium_max,
            "high_min": self.wl_high_min,
            "high_max": self.wl_high_max,
            "very_high_min": self.wl_very_high_min,
        }

    @property
    def frain_thresholds(self):
        return {
            "none_max": self.frain_none_max,
            "light_min": self.frain_light_min,
            "light_max": self.frain_light_max,
            "moderate_min": self.frain_moderate_min,
            "moderate_max": self.frain_moderate_max,
            "heavy_min": self.frain_heavy_min,
        }

    @property
    def ror_thresholds(self):
        return {
            "negative_max": self.ror_negative_max,
            "near_zero_min": self.ror_near_zero_min,
            "near_zero_max": self.ror_near_zero_max,
            "moderate_min": self.ror_moderate_min,
            "moderate_max": self.ror_moderate_max,
            "rapid_min": self.ror_rapid_min,
        }

    @property
    def tide_thresholds(self):
        return {
            "low_max": self.tide_low_max,
            "mid_min": self.tide_mid_min,
            "mid_max": self.tide_mid_max,
            "high_min": self.tide_high_min,
            "high_max": self.tide_high_max,
            "extreme_min": self.tide_extreme_min,
        }


settings = Settings()
