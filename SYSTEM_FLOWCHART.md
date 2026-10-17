# System Flowchart — River Monitor

```mermaid
flowchart TD
    %% ===== INPUTS =====
    subgraph INPUTS["External Inputs"]
        S["LoRa Water-Level Sensor\n(RFM95W @915MHz)"]
        W["Open-Meteo API\n(Weather + Marine/Tide)"]
        U["User / Browser"]
    end

    %% ===== RASPBERRY PI =====
    subgraph PI["Raspberry Pi 5"]
        LR["LoRa Receiver\n(1-min ingestion)"]
        WF["Weather & Tide Fetcher\n(6-hour cache)"]
        DB[("SQLite Database\nsensor_data, rainfall_daily,\nweather, tidal_data, predictions")]
        AI["AI Prediction Pipeline\nRandom Forest (8 features)\n+ Fuzzy Logic (20 rules)\nDual horizon: 24h & 48h"]
        WD["Web Dashboard\n(FastAPI)"]
        SH["SMS Handler\n(A7608e-H)"]
    end

    %% ===== OUTPUTS =====
    subgraph OUT["Outputs"]
        BR["Browser Dashboard\n(Charts, Status, Alerts)"]
        SMS["SMS Alerts\n(Alarm / Critical)"]
    end

    %% ===== FLOWS =====
    S -->|"Distance, Tips"| LR
    W -->|"Precip, Temp, Tide"| WF

    LR -->|"water level, rainfall"| DB
    WF -->|"forecast + tide"| DB

    DB -->|"latest sensor + weather"| AI
    AI -->|"risk level, propensity,\n7-day forecast"| DB
    AI -->|"Alarm/Critical"| SH

    DB -->|"status, levels,\npredictions"| WD
    WD -->|"HTML/JSON"| U
    U -->|"requests"| WD

    WD --> BR
    SH --> SMS

    classDef input fill:#e3f2fd,stroke:#1976d2
    classDef pi fill:#fff3e0,stroke:#f57c00
    classDef out fill:#e8f5e9,stroke:#388e3c
    class S,W,U input
    class LR,WF,DB,AI,WD,SH pi
    class BR,SMS out
```

## How to read
- **Inputs**: LoRa sensor (water level every minute), Open-Meteo API (weather/tide every 6 h), user via browser.
- **Processing (Raspberry Pi 5)**: LoRa receiver ingests data; weather fetcher caches forecasts; both persist to SQLite; AI pipeline runs RF + fuzzy logic for 24 h and 48 h horizons; web dashboard serves the UI; SMS handler sends alerts on Alarm/Critical.
- **Outputs**: Browser dashboard for monitoring; SMS alerts to configured phone numbers.
