# River Monitor System

A **LAN-accessible web dashboard** for real-time river water level monitoring and flood risk prediction using **LoRa sensors**, **SMS alerts**, **Open-Meteo weather/tide data**, **Random Forest + Fuzzy Logic AI** on **Raspberry Pi 5**.

## Features

- **Real-time Monitoring**: Water level data from LoRa-connected sensors (RFM95W @915MHz) every minute
- **SMS Alerts**: Send-only SMS notifications via the A7608e-H module to configured phone numbers when risk is high
- **Weather & Tide Integration**: 7-day forecast from Open-Meteo (precipitation, max/min temp, tide levels)
- **AI Prediction**: Random Forest (8 features) + Fuzzy Logic (20 rules) for flood risk classification
- **Dual-Horizon Prediction**: 24h and 48h flood risk predictions computed and displayed side by side
- **Fuzzy Logic Risk Levels**: Receding, Alert, Alarm, Critical based on 5 inputs
- **Web Dashboard**: Responsive, real-time dashboard with charts, fuzzy logic details, and status monitoring

## System Architecture

```
+------------------+     +------------------+     +------------------+
|   LoRa Sensor    |     |   SMS Module     |     |  Open-Meteo API  |
|  (RFM95W @915MHz)|     |  (A7608e-H)      |     | (Weather + Tide) |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         v                        v                        v
+------------------------------------------------------------------+
|                        Raspberry Pi 5                            |
|  +------------------+  +------------------+  +------------------+ |
|  |  LoRa Receiver   |  |  SMS Handler     |  | Weather/Tide     | |
|  |  (1-min data)    |  |  (alerts)        |  | Fetcher (6-hr)   | |
|  +--------+---------+  +--------+---------+  +--------+---------+ |
|           |                  |                        |            |
|           v                  v                        v            |
|  +----------------------------------------------------------------+ |
|  |                         SQLite Database                         | |
|  +----------------------------------------------------------------+ |
|           |                                                  |
|           v                                                  v
|  +------------------+                              +------------------+ |
|  |  AI Pipeline     |                              | Web Dashboard    | |
|  |  RF (8 features) |                              | (FastAPI)        | |
|  |  + Fuzzy Logic   |                              |                  | |
|  |  (20 rules)      |                              |                  | |
|  +--------+---------+                              +--------+---------+ |
|           |                                                  |
|           +--------------------------------------------------+ |
|                              |                                   |
|                              v                                   v
|                     +------------------+              +------------------+
|                     |  SMS Alerts      |              |  Browser         |
|                     +------------------+              +------------------+
+------------------------------------------------------------------+
```

## AI Pipeline

### Random Forest Model (8 Features)

Features are computed per horizon. `ref_day` is **today** for the 24h forecast and **tomorrow** for the 48h forecast. Rainfall blends sensor-measured accumulation (`rainfall_daily` table) with Open-Meteo forecast:

| Feature | Description | Source |
|---------|-------------|--------|
| R1 | 1-day precipitation sum (ref_day) | Sensor daily + Open-Meteo forecast |
| R3 | 3-day precipitation sum (ref_day-2 .. ref_day) | Sensor daily + Open-Meteo forecast |
| R7 | 7-day precipitation sum (ref_day-6 .. ref_day) | Sensor daily + Open-Meteo forecast |
| rain_days | Consecutive rainy days ending on ref_day (`precipitation > RAIN_DAY_THRESHOLD_MM`) | Sensor daily + Open-Meteo forecast |
| TMAX | Daily maximum temperature (ref_day) | Open-Meteo |
| TMIN | Daily minimum temperature (ref_day) | Open-Meteo |
| TideMax | Maximum tide level in 7-day forecast | Open-Meteo Marine |
| TideMin | Minimum tide level in 7-day forecast | Open-Meteo Marine |

**Output**: Flood Propensity (Low=0, Medium=1, High=2)

### Fuzzy Logic System (20 Rules)
**Inputs** (5 fuzzy variables):
| Variable | Terms |
|----------|-------|
| Water Level (WL) | Low, Medium, High, Very High |
| Rate-of-Rise (RoR) | Negative, Near-Zero, Moderate, Rapid |
| Forecast Rain (FRain) | None, Light, Moderate, Heavy |
| Tide Level (Tide) | Low, Mid, High, Extreme |
| RF Flood Propensity (RF) | Low, Medium, High |

**Output**: Flood Risk Level (Receding, Alert, Alarm, Critical)

**Membership Functions**:
- WL: Low <610mm, Medium 610-1220mm, High 1220-1830mm, Very High >1830mm
- FRain: None <5mm, Light 5-15mm, Moderate 15-30mm, Heavy >30mm
- RoR: Negative <-0.5mm/hr, Near-Zero -0.5 to 0.5, Moderate 0.5-4.0, Rapid >4.0
- Tide: Low <0.5m, Mid 0.5-1.0m, High 1.0-1.5m, Extreme >1.5m

## Project Structure

```
river-monitor/
├── data/
│   ├── river_monitor.db          # SQLite database
│   ├── models/
│   │   ├── rf_model.pkl          # Trained Random Forest model
│   │   └── scaler.pkl            # Feature scaler
│   └── weather_cache/             # Cached weather API responses
├── src/
│   ├── config.py                 # Configuration file
│   ├── data/
│   │   ├── __init__.py
│   │   ├── database.py           # Database operations + migration
│   │   ├── lora_receiver.py      # LoRa data ingestion (1-min)
│   │   ├── sms_handler.py        # SMS alert sending
│   │   └── weather_fetcher.py    # Open-Meteo weather + tide client
│   ├── model/
│   │   ├── __init__.py
│   │   ├── preprocess.py         # Data preprocessing (RF features)
│   │   ├── train.py              # Model training (new 8-feature mode)
│   │   ├── predict.py            # Prediction logic (RF + Fuzzy)
│   │   └── fuzzy_logic.py        # Fuzzy inference system (20 rules)
│   └── web/
│       ├── __init__.py
│       ├── main.py               # FastAPI backend + fuzzy API
│       ├── static/
│       │   └── style.css         # Dashboard styles
│       └── templates/
│           └── index.html        # Dashboard HTML
├── migrate_db.py                 # Database migration script
├── requirements.txt              # Python dependencies
├── setup.sh                      # Setup script
└── README.md                     # This file
```

## Hardware Requirements

| Component | Model | Connection | Purpose |
|-----------|-------|------------|---------|
| Raspberry Pi 5 | - | - | Main processing unit |
| LoRa Module | RFM95W | SPI | Receive sensor data (1-min) |
| SMS Module | A7608e-H | UART | Send SMS alerts (send-only) |
| Water Level Sensor | - | LoRa | Measure river water level (mm) |

### Wiring Guide

#### RFM95W (LoRa Module)

| RFM95W Pin | Raspberry Pi 5 Pin | GPIO |
|-----------|-------------------|------|
| VCC | 3.3V (Pin 1) | - |
| GND | GND (Pin 6) | - |
| SCK | GPIO11 (Pin 23) | 11 |
| MISO | GPIO9 (Pin 21) | 9 |
| MOSI | GPIO10 (Pin 19) | 10 |
| CS | GPIO8 (Pin 24) | 8 |
| RST | GPIO27 (Pin 13) | 27 |
| DIO0 | GPIO25 (Pin 22) | 25 |

#### A7608e-H (SMS Module)

| A7608e-H Pin | Raspberry Pi 5 Pin | UART |
|-------------|-------------------|------|
| VCC | 5V (Pin 2) | - |
| GND | GND (Pin 6) | - |
| TXD | UART RX (Pin 10) | - |
| RXD | UART TX (Pin 8) | - |

## Software Requirements

- **Operating System**: Raspberry Pi OS Lite (64-bit) recommended
- **Python**: 3.11 or higher
- **Dependencies**: See `requirements.txt` (includes `scikit-fuzzy>=0.5.0`)

## Setup Instructions

### 1. Prepare Raspberry Pi 5

1. **Flash Raspberry Pi OS Lite (64-bit)**
   ```bash
   # Use Raspberry Pi Imager or manually flash the image
   ```

2. **Enable SSH and configure network**
   - Create an empty `ssh` file in the boot partition for headless setup
   - Configure WiFi by creating `wpa_supplicant.conf` in the boot partition:
     ```
     ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
     update_config=1
     country=PH
     
     network={
         ssid="YourSSID"
         psk="YourPassword"
         key_mgmt=WPA-PSK
     }
     ```

3. **Boot the Raspberry Pi and SSH in**
   ```bash
   ssh pi@raspberrypi.local
   # Default password: raspberry
   ```

### 2. Clone and Setup the Project

1. **Clone the repository** (or copy the files)
   ```bash
   git clone <repository-url>
   cd river-monitor
   ```

2. **Run the setup script**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. **Configure the system**
   Edit `src/config.py`:
   ```python
   # Required settings
   ALERT_PHONE_NUMBERS = ["+639123456789"]  # Your phone numbers
   
   # Optional: Adjust based on your location
   WEATHER_LATITUDE = 14.5995  # Manila coordinates
   WEATHER_LONGITUDE = 120.9842
   
   # Adjust after hydrological survey
   CRITICAL_LEVEL_M = 2.0  # Water level at 100% risk
   ```

### 3. Train the AI Model

**Note**: Training is resource-intensive. Do this on a PC with more resources, then transfer the model to the Raspberry Pi.

1. **Prepare your training data**
   - CSV with columns: `R1, R3, R7, rain_days, TMAX, TMIN, TideMax, TideMin, target`
   - Target values: `0`=Low, `1`=Medium, `2`=High flood propensity
   - Based on 5-year historical data with known flood events
   - Generate a starter file with `python create_template.py` (writes `training_template.csv`)

2. **Train the model**
   ```bash
   # On your PC (not Raspberry Pi)
   python src/model/train.py --mode new --csv training_data.csv --output data/models/rf_model.pkl
   ```

3. **Transfer the model to Raspberry Pi**
   ```bash
   # From your PC, copy to Raspberry Pi
   scp data/models/rf_model.pkl pi@raspberrypi.local:~/river-monitor/data/models/
   scp data/models/scaler.pkl pi@raspberrypi.local:~/river-monitor/data/models/
   ```

### 4. Run Database Migration

```bash
python migrate_db.py
```

### 5. Start the System

#### Option A: Manual Start
```bash
# Activate virtual environment
source venv/bin/activate

# Start the web dashboard
python src/web/main.py

# In separate terminals, start the data collectors
python src/data/lora_receiver.py
# SMS handler is invoked on demand for high-risk alerts
```

#### Option B: Systemd Service (Recommended)
```bash
# Start the service
sudo systemctl start river-monitor

# Check status
sudo systemctl status river-monitor

# View logs
sudo journalctl -u river-monitor -f
```

### 6. Access the Dashboard

Open a web browser and go to:
```
http://<raspberry-pi-ip>:8000
```

Replace `<raspberry-pi-ip>` with your Raspberry Pi's local IP address.

## Usage

### Dashboard Features

1. **Current Status**
   - Current water level (meters)
   - 24h risk level (color-coded: Receding/Alert/Alarm/Critical)
   - 48h risk level (color-coded: Receding/Alert/Alarm/Critical)
   - RF Propensity (Low/Medium/High) for both horizons
   - Last update time
   - Data source (LoRa)

2. **Water Level Chart**
   - Shows water level over the last 24 hours (1-min resolution)

3. **7-Day Forecast Chart**
   - Predicted water levels for the next 7 days
   - Risk threshold lines (Alert @40%, Alarm @60%, Critical @100%)

4. **Current Weather & Rainfall**
   - Precipitation (mm)
   - Temperature Max/Min (°C)
   - Tide Level (m)
   - Rainfall 24h total (mm) and tips

5. **Fuzzy Logic Details**
   - RF Propensity (Low/Medium/High) for 24h and 48h
   - Rule Triggered (1-20) for 24h and 48h
   - Shared inputs: Water Level (mm), Rate of Rise (mm/hr)
   - 24h inputs: Forecast Rain (mm), Tide Level (m)
   - 48h inputs: Forecast Rain (mm, tomorrow), Tide Level (m, same time tomorrow)

6. **System Status**
   - LoRa module connectivity
   - SMS module connectivity
   - Weather API status
   - Prediction model status

7. **Recent Alerts**
   - List of SMS alerts sent
   - Risk level, message, and status

### Manual Actions

- **Refresh Prediction**: Click the "Refresh Prediction" button to generate a new prediction
- **Test SMS Alert**: Click the "Test SMS Alert" button to send a test SMS
- **Refetch Forecast**: Click the "Refetch Forecast" button on the Current Weather card (admin) to immediately pull a fresh 7-day weather and tidal forecast from Open-Meteo, bypassing the 6-hour cache

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard HTML |
| `/api/status` | GET | System status |
| `/api/water-levels?hours=N` | GET | Water levels (last N hours) |
| `/api/weather?hours=N` | GET | Weather data (last N hours) |
| `/api/prediction` | GET | Latest prediction (RF + Fuzzy) |
| `/api/fuzzy-details` | GET | Detailed fuzzy logic info |
| `/api/forecast?days=N` | GET | Water level forecast (next N days) |
| `/api/alerts?limit=N` | GET | Recent alerts |
| `/api/rainfall?hours=N` | GET | Rainfall data (last N hours) |
| `/api/stats` | GET | Database statistics |
| `/api/refresh-prediction` | POST | Trigger new prediction |
| `/api/refresh-weather` | POST | Refetch weather + tide forecast (admin) |
| `/api/test-alert` | POST | Send test SMS alert |
| `/api/auth/login` | POST | Sign in (JSON `{username, password}`) |
| `/api/auth/logout` | POST | Sign out |
| `/api/auth/me` | GET | Current session user and role |
| `/api/sensor-health?window_hours=N` | GET | Sensor freshness, throughput and gaps |
| `/api/alerts?risk_level=&acknowledged=&start=&end=` | GET | Filtered alerts |
| `/api/alerts/stats` | GET | Acknowledged/outstanding alert counts |
| `/api/alerts/{id}/acknowledge` | POST | Acknowledge an alert (admin) |
| `/api/users` | GET/POST | List/create users (admin) |
| `/api/users/{id}` | PUT/DELETE | Update/delete user (admin) |
| `/api/audit?limit=N` | GET | Recent audit entries (admin) |
| `/healthz` | GET | Liveness probe |
| `/readyz` | GET | Readiness probe (DB, model, weather) |

## Data Flow

1. **Sensor Data Collection** (every minute)
   - LoRa sensor sends: `Distance=<mm>,Tips=<count>`
   - Distance converted to water level: `water_level = 2.5m - distance`
   - Rain tips converted to rainfall: `rainfall = tips * 0.2mm`
   - Data stored in SQLite `sensor_data` table with source="lora"
   - Daily rainfall totals aggregated into `rainfall_daily` (threshold: `RAIN_DAY_THRESHOLD_MM`)

2. **Stale-Data Warning** (5 min timeout)
   - If no LoRa data for 5 minutes, the receiver logs a warning
   - Sensor is LoRa-only; there is no SMS data fallback

3. **Weather & Tide Data** (every 6 hours)
   - Fetched from Open-Meteo API (weather + marine)
   - Cached locally for 6 hours
   - Includes: precipitation, temp max/min, tide max/min
   - Tide forecasts persisted hourly to `tidal_data` for current-location tide lookups

4. **Prediction Pipeline** (on-demand + auto)
   - Get latest 1-min water level data (`sensor_data` table)
   - Compute RoR from last 5 minutes
   - Get weather/tide features for both horizons (24h ref=today, 48h ref=tomorrow)
   - Run RF model → propensity (Low/Medium/High) for 24h and 48h
   - Run Fuzzy Logic (20 rules) → risk level for 24h and 48h
   - Generate 7-day forecast
   - Store one prediction row with both horizons' results (24h columns + `_48h` columns)

5. **Alerting**
   - When prediction is "Alarm" or "Critical", SMS alerts sent
   - Alerts include current water level and 1-day forecast change

6. **Receding Detection**
   - Handled by fuzzy rules (Rules 1, 2, 3, 12, 13)
   - No separate check needed

## Configuration

### Environment Variables (`.env`)

Runtime settings are loaded from `.env` (see `.env.example`) via `src/settings.py`. Copy the example and edit:

```bash
cp .env.example .env
```

Key variables include `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `AUTH_ENABLED`, `DASHBOARD_HOST/PORT`, `WEATHER_LATITUDE/LONGITUDE`, hardware ports/pins, and alert thresholds. Logs are written to `logs/river-monitor-YYYY-MM-DD.log`.

### Fuzzy Logic Thresholds

Edit `src/config.py`:

```python
# Water Level (mm)
WL_THRESHOLDS = {
    'low_max': 610,
    'medium_min': 610, 'medium_max': 1220,
    'high_min': 1220, 'high_max': 1830,
    'very_high_min': 1830
}

# Forecast Rain (mm/day)
FRAIN_THRESHOLDS = {
    'none_max': 5,
    'light_min': 5, 'light_max': 15,
    'moderate_min': 15, 'moderate_max': 30,
    'heavy_min': 30
}

# Rate of Rise (mm/hr)
ROR_THRESHOLDS = {
    'negative_max': -0.5,
    'near_zero_min': -0.5, 'near_zero_max': 0.5,
    'moderate_min': 0.5, 'moderate_max': 4.0,
    'rapid_min': 4.0
}

# Tide Level (meters)
TIDE_THRESHOLDS = {
    'low_max': 0.5,
    'mid_min': 0.5, 'mid_max': 1.0,
    'high_min': 1.0, 'high_max': 1.5,
    'extreme_min': 1.5
}
```

### RF Model Features
```python
RF_FEATURES = ['R1', 'R3', 'R7', 'rain_days', 'TMAX', 'TMIN', 'TideMax', 'TideMin']
RAIN_DAY_THRESHOLD_MM = 2.0  # Min precipitation (mm) for a day to count as a "rain day"
RF_CLASSES = {0: 'Low', 1: 'Medium', 2: 'High'}
```

## Troubleshooting

### LoRa Module Not Working
1. Check wiring (SPI connections)
2. Verify LoRa module is properly configured for 915MHz
3. Check if SPI is enabled: `ls /dev/spi*`

### SMS Module Not Working
1. Check wiring (UART connections)
2. Verify SIM card is inserted and has signal
3. Check if UART is enabled and Bluetooth is disabled
4. Test with AT commands: `screen /dev/ttyS0 115200`

### Weather/Tide API Not Working
1. Check internet connectivity: `ping api.open-meteo.com`
2. Test API manually:
   ```bash
   curl "https://api.open-meteo.com/v1/forecast?latitude=14.5995&longitude=120.9842&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=auto&forecast_days=7"
   curl "https://marine-api.open-meteo.com/v1/marine?latitude=14.5995&longitude=120.9842&daily=tide_level_max,tide_level_min&timezone=auto&forecast_days=7"
   ```

### Model Not Loading
1. Verify model files exist: `ls -l data/models/`
2. Check if model was trained with 8 features (including TideMin)
3. Re-train the model and transfer to Raspberry Pi

### Dashboard Not Accessible
1. Check if service is running: `sudo systemctl status river-monitor`
2. Check logs: `sudo journalctl -u river-monitor -f`
3. Test locally: `curl http://localhost:8000`

## Maintenance

### Database Cleanup
```bash
python -c "from src.data.database import cleanup_old_data; cleanup_old_data(days=30)"
```

### Model Retraining
1. Export data from the database
2. Combine with historical data
3. Add target column (0=Low, 1=Medium, 2=High)
4. Retrain: `python src/model/train.py --mode new --csv training_data.csv`
5. Transfer new model to Raspberry Pi

### System Updates
```bash
sudo apt update && sudo apt upgrade -y
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

## Security Considerations

1. **LAN Access Only**: Dashboard only accessible on local network
2. **Session Authentication**: Cookie-based sessions with PBKDF2-HMAC-SHA256 password hashes; two roles (`viewer` read-only, `admin` may change settings, contacts, alerts and users)
3. **First-run credentials**: A default `admin`/`admin` account is created when the user table is empty. Set `ADMIN_PASSWORD` and a random `SECRET_KEY` in `.env` before deployment.
4. **Audit Trail**: Mutating actions are recorded in the `audit_log` table and viewable from the Admin page.
5. **SMS Costs**: Be aware of SMS costs when sending alerts

## Future Enhancements

- [x] Add user authentication to the dashboard
- [ ] Implement HTTPS for secure connections
- [ ] Add more sophisticated time series forecasting (LSTM, ARIMA)
- [ ] Implement edge computing for faster predictions
- [ ] Add support for multiple sensor locations
- [ ] Implement data export functionality
- [ ] Add email alerts in addition to SMS
- [ ] Implement a mobile app for remote monitoring

## License

This project is provided as-is for educational and research purposes.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a pull request

## Acknowledgments

- **PAGASA** for flood risk classification standards
- **Open-Meteo** for free weather and marine/tide APIs
- **Raspberry Pi Foundation** for the hardware platform
- **scikit-learn** for the machine learning library
- **scikit-fuzzy** for the fuzzy logic library

---

**Developed for Thesis Project**

For questions or issues, please refer to your project documentation or contact your supervisor.