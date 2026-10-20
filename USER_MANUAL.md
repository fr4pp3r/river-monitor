# River Monitor — User Manual

**A Practical Guide to the River Water Level Monitoring & Flood Risk Prediction Dashboard**

Version 1.0 · October 2026

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Getting Started](#2-getting-started)
3. [Signing In](#3-signing-in)
4. [Dashboard Overview](#4-dashboard-overview)
   - 4.1 [Current Status](#41-current-status)
   - 4.2 [Risk Gauge](#42-risk-gauge)
   - 4.3 [System Status](#43-system-status)
   - 4.4 [Water Level Chart](#44-water-level-chart)
   - 4.5 [7-Day Water Level Forecast](#45-7-day-water-level-forecast)
   - 4.6 [Current Weather & Rainfall](#46-current-weather--rainfall)
   - 4.7 [Fuzzy Logic Details](#47-fuzzy-logic-details)
   - 4.8 [Alert Contacts](#48-alert-contacts)
   - 4.9 [Sensor Health](#49-sensor-health)
   - 4.10 [Alerts](#410-alerts)
5. [Understanding Risk Levels](#5-understanding-risk-levels)
6. [The Fuzzy Rules Page](#6-the-fuzzy-rules-page)
7. [The Settings Page](#7-the-settings-page)
8. [The Database Page](#8-the-database-page)
9. [The Admin Page (Administrators Only)](#9-the-admin-page-administrators-only)
10. [User Accounts & Roles](#10-user-accounts--roles)
11. [Daily Operating Procedures](#11-daily-operating-procedures)
12. [Troubleshooting](#12-troubleshooting)
13. [Frequently Asked Questions](#13-frequently-asked-questions)
14. [Glossary](#14-glossary)

---

## 1. Introduction

### What is River Monitor?

River Monitor is a real-time river water level monitoring and flood risk prediction system. It runs on a Raspberry Pi at a monitoring station and is accessed through a web dashboard on any device (computer, tablet, or phone) connected to the same local network.

The system continuously:

- **Measures** the river's water level using a LoRa-connected ultrasonic sensor (one reading every minute)
- **Tracks** rainfall using a tipping-bucket rain gauge
- **Fetches** weather and tide forecasts from the Open-Meteo API (every 6 hours)
- **Predicts** flood risk for the next **24 hours** and **48 hours** using a two-stage AI pipeline (Random Forest + Fuzzy Logic)
- **Sends SMS alerts** to configured contacts when the risk reaches **Alarm** or **Critical** levels

### Who Should Use This Manual?

This manual is written for two audiences:

| Role | What you'll use most |
|------|---------------------|
| **Operators / Duty Monitors** | Dashboard, Alerts, Alert Contacts, Sensor Health |
| **Administrators** | Everything above, plus Settings, Database, Admin page, user management |

### What You Need

- A device with a web browser (Chrome, Firefox, Edge, or Safari)
- A device connected to the same private network as the River Monitor station: the station's **home LAN**, or the **phone hotspot** it joins out in the field (see the table below)
- A user account (see [Section 10](#10-user-accounts--roles))

> **Note:** The dashboard is only reachable from the private network the station is connected to. It is never exposed to the public internet.

---

## 2. Getting Started

### Finding the Dashboard Address

The dashboard runs on a Raspberry Pi at a default address of **port 8000**. Ask your system administrator for the station's IP address, then open a browser and go to:

```
http://<station-ip-address>:8000
```

For example, if the station's IP address is `192.168.1.50`, you would visit:

```
http://192.168.1.50:8000
```

### Ways to Reach the Dashboard

The station answers at the same name on every private network it joins:

| Where you are | What to open |
|---|---|
| On the station's home LAN | `http://raspberrypi.local:8000` or `http://<station-ip>:8000` |
| In the field, on the phone hotspot the station auto-joins | `http://raspberrypi.local:8000` or the hotspot's LAN IP |

The `raspberrypi.local` address (mDNS) works from most current phones, laptops and desktops without knowing the IP; if a device does not resolve it, use the IP address of the network you are both on.

If the administrator has set up **phone-hotspot autoconnect**, the station automatically joins the administrator's phone hotspot whenever it is nearby. That keeps its internet data current in the field and puts the station on the hotspot's network, so people connected to the same phone hotspot open the dashboard as usual. While it is on the phone hotspot, the station is not connected to other WiFi networks. See README.md (Remote Access → Field use) for how this is configured.

### Supported Devices

The dashboard is responsive and works on:

- Desktop and laptop computers
- Tablets
- Mobile phones

The layout adapts to smaller screens automatically.

---

## 3. Signing In

When you open the dashboard for the first time in a browser session, you'll be taken to the **Sign In** page.

### Steps

1. Enter your **Username**
2. Enter your **Password**
3. Click **Sign In**

If your credentials are correct, you'll be taken to the Dashboard. If they're wrong, an error message appears — re-check your credentials and try again.

### First-Time Login

When the system is first installed (and no users exist yet), a default administrator account is created automatically:

| Field | Default Value |
|-------|---------------|
| Username | `admin` |
| Password | `admin` |

> ⚠️ **Important:** The administrator should change this default password immediately after first login. See [Section 9.5](#95-changing-your-password--security) on the Admin page.

### Logging Out

Your username and role appear in the **top-right corner** of the header. Click **Logout** to end your session.

### Session Timeout

Sessions expire after **12 hours** of inactivity by default. If your session expires, you'll simply be asked to sign in again.

---

## 4. Dashboard Overview

The Dashboard is the main monitoring screen, organized into cards. Use the **navigation bar** at the top to move between pages:

| Page | Who sees it | Purpose |
|------|------------|---------|
| **Dashboard** | All users | Live monitoring, charts, alerts |
| **Settings** | Admins (editable); Viewers (read-only) | System configuration |
| **Database** | All users | Browse and download stored data |
| **Fuzzy Rules** | All users | Reference: the 20 AI decision rules |
| **Admin** | Admins only | User management and audit log |

The dashboard **auto-refreshes** every 30 seconds by default.

---

### 4.1 Current Status

The **Current Status** card (top-left) is the most important panel. It shows:

| Field | What It Means |
|-------|--------------|
| **Water Level** | Current river water level in meters above the sensor baseline |
| **Rainfall** | Rainfall measured this hour (mm), from the rain gauge |
| **Trend** | Whether the water level is rising, falling, or stable (over the last 24 hours) |
| **Last Updated** | How long ago the most recent sensor reading arrived |
| **Data Source** | Where the current reading came from (LoRa radio link) |

At the top of the card, two **risk badges** display the current flood risk:

- **24h** — the risk level for the next 24 hours
- **48h** — the risk level for the next 48 hours

Each badge is color-coded (see [Section 5](#5-understanding-risk-levels)).

A green pulsing **live indicator** with the text "Live" confirms that data is flowing. If the text changes to "Waiting for data…", no recent sensor reading is available.

### Action Buttons

| Button | What It Does |
|--------|-------------|
| **Refresh Prediction** | Immediately runs a new AI prediction using the latest sensor and weather data (instead of waiting for the automatic 5-minute cycle) |
| **Test SMS Alert** | Sends a test SMS message to all active alert contacts (to verify the SMS module is working) |
| **Update Rainfall Totals** | Recalculates daily rainfall totals from the raw rain-gauge data |

> **Note for Viewers:** The *Refresh Prediction* and *Update Rainfall Totals* buttons work for all users. *Test SMS Alert* requires an administrator account.

---

### 4.2 Risk Gauge

Below the status values, a horizontal **gauge** visualizes where the current water level sits relative to the three risk thresholds:

```
Normal  ────── Alert ────── Alarm ────── Critical
  0%          40%           60%           100%
```

- The **needle** shows the current level as a percentage of the critical level.
- The **legend** below shows the actual water level (in meters) at which each threshold is crossed, e.g.:
  - Alert ≥ 0.8 m
  - Alarm ≥ 1.2 m
  - Critical ≥ 2.0 m

These threshold levels are set by the administrator in [Settings](#7-the-settings-page) based on a hydrological survey of the river.

---

### 4.3 System Status

The **System Status** card (top-right) shows the health of the four main system components:

| Component | Healthy Meaning |
|-----------|----------------|
| **LoRa Module** | The LoRa radio receiver is online and receiving sensor data |
| **SMS Module** | The SMS modem is ready (or disabled, if turned off in Settings) |
| **Weather API** | The Open-Meteo weather/tide connection is working |
| **Prediction Model** | The AI model file loaded successfully and is ready to predict |

Each component shows a colored status badge: **OK**, **Error**, or **Disabled**. If any component shows an error, see [Troubleshooting](#12-troubleshooting).

---

### 4.4 Water Level Chart

A line chart showing the river's water level over the **last 24 hours**, plotted from LoRa sensor readings (one point per minute).

- Use this chart to see rising or falling trends at a glance.
- If no data is available yet, the chart shows "Waiting for the first sensor reading…"

---

### 4.5 7-Day Water Level Forecast

A line chart showing the **predicted water level for the next 7 days**, generated by the AI pipeline. Horizontal reference lines mark the **Alert**, **Alarm**, and **Critical** thresholds so you can see at a glance when the forecast is expected to cross them.

- The forecast blends rainfall, temperature, and tide predictions with the current water level.
- If the forecast line approaches or crosses a threshold, treat it as an early warning.

---

### 4.6 Current Weather & Rainfall

Shows current weather conditions and recent rainfall:

| Field | Meaning |
|-------|---------|
| **Precipitation** | Rainfall from the weather forecast (mm) |
| **Pressure** | Barometric pressure (hPa) |
| **Temperature** | Current temperature (°C) |
| **Humidity** | Relative humidity (%) |
| **Rainfall (24h)** | Total rainfall measured by the rain gauge in the last 24 hours (mm) |
| **Rain Tips (24h)** | Number of rain-gauge tips recorded in the last 24 hours |

> **Admins:** A **Refetch Forecast** button appears in this card's header. Click it to immediately pull a fresh 7-day weather and tide forecast from Open-Meteo, bypassing the normal 6-hour cache. Use this if the weather data looks stale.

---

### 4.7 Fuzzy Logic Details

This card shows the "thinking" behind the current risk prediction, for both the 24-hour and 48-hour horizons.

**Shared inputs** (same for both horizons):

| Input | Meaning |
|-------|---------|
| **Water Level** | Current water level (mm) |
| **Rate of Rise** | How fast the water level is changing (mm/hour) |

**Per-horizon inputs:**

| Input | Meaning |
|-------|---------|
| **RF Propensity** | The Random Forest model's flood propensity classification: Low, Medium, or High |
| **Rule Triggered** | Which of the 20 fuzzy rules fired (rule number 1–20) |
| **Forecast Rain** | Forecast rainfall for that horizon (mm) — for the 48h horizon, this is tomorrow's forecast |
| **Tide Level** | Forecast tide level (m) — for the 48h horizon, this is the tide at the same time tomorrow |

You can look up any rule number on the [Fuzzy Rules page](#6-the-fuzzy-rules-page).

---

### 4.8 Alert Contacts

This card lists the phone contacts who receive SMS flood alerts.

- **Contacts** show each person's name, phone number, and whether they are active.
- **Add Contact** (admin) opens a form to add a new recipient.
- **Send Test Message** (admin) sends a test SMS to all active contacts to verify delivery.

Only contacts marked **active** receive alerts. Deactivate a contact (rather than deleting them) if they should temporarily stop receiving messages.

See [Section 11.2](#112-managing-alert-contacts) for procedures.

---

### 4.9 Sensor Health

The **Sensor Health** card reports on the reliability of the LoRa sensor link:

- **Data freshness** — how long since the last reading
- **Throughput** — how many readings arrived in the recent window
- **Gaps** — any periods where no data arrived

A badge in the card's header summarizes overall status: **OK**, **Degraded**, or **Unknown**.

If the badge shows *Degraded* or readings are stale, see [Troubleshooting](#12-troubleshooting).

---

### 4.10 Alerts

The **Alerts** card lists SMS flood alerts that have been generated, most recent first.

**Filters** let you narrow the list:

| Filter | Options |
|--------|---------|
| **Risk** | All, Receding, Alert, Alarm, Critical |
| **Status** | All, Outstanding, Acknowledged |
| **From / To** | A date range |

Click **Refresh** to reload the list.

**Acknowledging alerts (admins):** Each unacknowledged alert can be **acknowledged** to mark it as seen and handled. Acknowledged alerts show who acknowledged them and when. This creates a clear record that someone has responded. A count of outstanding (unacknowledged) alerts appears at the top of the card.

> **Viewers** can see the alerts list but cannot acknowledge alerts. Only administrators can acknowledge.

---

## 5. Understanding Risk Levels

The system classifies flood risk into four levels. Learn these well — they drive the dashboard colors, the risk badges, and SMS alerts.

| Level | Color | Meaning | Recommended Action |
|-------|-------|---------|-------------------|
| **Receding** | Green | Water level is falling after a high-water period. | Normal monitoring. Risk is decreasing. |
| **Normal / Low** | Blue-Green | Water level is well below thresholds. | Routine monitoring. |
| **Alert** | Yellow/Amber | Water level or forecast is approaching caution levels. | Increase vigilance. Brief responders. Monitor closely. |
| **Alarm** | Orange | Conditions indicate likely flooding. | Prepare response. Verify contacts are reachable. |
| **Critical** | Red | Immediate flood danger. | Activate emergency response. Evacuate as needed. |

### Risk Horizons

Every prediction is made for **two horizons**:

- **24-hour (1-day) horizon** — risk for today, using today's weather forecast
- **48-hour (2-day) horizon** — risk for tomorrow, using tomorrow's weather forecast

The 48-hour horizon gives you advance warning: if the 48h badge is higher than the 24h badge, conditions are expected to worsen.

### SMS Alert Triggering

By default, SMS alerts are sent only when the risk level is **Alarm** or **Critical**. Administrators can change which levels trigger SMS in [Settings](#71-sms-alert-configuration).

To avoid flooding contacts with repeated messages, the system enforces a **cooldown period** (default: 30 minutes) between alerts to the same recipient.

---

## 6. The Fuzzy Rules Page

The **Fuzzy Rules** page is a reference documenting the 20 fuzzy inference rules that produce the final risk level. It's useful when you want to understand *why* the system chose a particular risk level.

### What's on the Page

1. **Input Variables & Membership Functions** — Shows each fuzzy input (Water Level, Rate of Rise, Forecast Rain, Tide, RF Propensity) and how continuous values map to linguistic terms (e.g. Water Level: Low < 610 mm, Medium 610–1220 mm, High 1220–1830 mm, Very High > 1830 mm).

2. **Output Variable: Flood Risk Level** — Shows the four output terms (Receding, Alert, Alarm, Critical).

3. **Rules Table** — All 20 rules (15 original + 5 gap-fill rules added to cover uncovered input combinations). Each row shows:
   - **Rule #**
   - **Conditions** — the IF part, e.g. "WL is High AND RoR is Rapid AND FRain is Heavy…"
   - **Output Risk** — the THEN result (Receding / Alert / Alarm / Critical)
   - **Type** — Original (1–15) or Gap-Fill (16–20)

### Using the Filters

- **Filter by Risk Level** — show only rules that output a given risk level
- **Rule Type** — show only original rules or only gap-fill rules
- **Expand All / Collapse All** — show or hide the full condition details for every rule

When the Fuzzy Logic Details card on the Dashboard shows "Rule Triggered: 7", find rule 7 in this table to see exactly which conditions led to the current risk level.

---

## 7. The Settings Page

> **Administrators only.** Viewers see the Settings page but all fields are read-only, with a note: *"You are signed in as a viewer. Settings are read-only."*

The Settings page is organized into sections. After making changes, click **Save Settings** at the bottom. You can also **Reset to Defaults** or **Restart Server**.

> ⚠️ **Restart required:** Some settings (Host, Port) only take effect after a server restart. A note at the top of the page reminds you of this.

### 7.1 Module Control

Enable or disable the hardware modules:

| Toggle | Effect |
|--------|--------|
| **LoRa Receiver** | Turn the LoRa water-level receiver on or off |
| **SMS Handler** | Turn SMS alert sending on or off |

Disabling the SMS Handler stops all outgoing alert messages. Use this during maintenance.

### 7.2 LoRa Hardware

Radio configuration for the RFM95W LoRa module. **Do not change these unless you know the hardware configuration**, or you may lose the sensor link.

| Setting | Default | Notes |
|---------|---------|-------|
| SPI Port | 0 | SPI bus number |
| CE Pin / CS Pin / Reset Pin | 5 / 8 / 22 | GPIO pin assignments |
| Frequency | 915.0 MHz | Must match the remote sensor's frequency |
| Bandwidth | 125 kHz | Radio bandwidth |
| Spreading Factor | 7 | Higher = longer range, slower data |
| Coding Rate | 5 | Error-correction coding rate |

### 7.3 SMS Hardware

Configuration for the A7608e-H SMS modem:

| Setting | Default | Notes |
|---------|---------|-------|
| UART Port | /dev/ttyUSB2 | Serial device path |
| Baud Rate | 115200 | Serial communication speed |
| Timeout | 5 seconds | Response timeout |

### 7.4 Sensor Configuration

Calibration values for the ultrasonic distance sensor and rain gauge:

| Setting | Default | Notes |
|---------|---------|-------|
| **Max Sensor Distance** | 2.5 meters | The sensor's mounting height above the riverbed. Water level = this value − measured distance. Recalibrate after any sensor repositioning. |
| **Rain Bucket Tip** | 0.2 mm | Rainfall per rain-gauge tip. Check your gauge's specification. |

### 7.5 Risk Thresholds

| Setting | Default | Notes |
|---------|---------|-------|
| **Critical Water Level** | 2.0 meters | The water level at which risk = 100% (Critical). Set this after a hydrological survey. |
| **Receding Hours** | 2 hours | How many hours the level must be dropping before the risk is classified "Receding". |

**Risk Threshold Ratios** (as fractions of the critical level):

| Transition | Default | Effective Level |
|-----------|---------|-----------------|
| Normal → Alert | 0.40 | 40% of critical (0.8 m) |
| Alert → Alarm | 0.60 | 60% of critical (1.2 m) |
| Alarm → Critical | 1.00 | 100% of critical (2.0 m) |

### 7.6 Weather API

| Setting | Default | Notes |
|---------|---------|-------|
| **Latitude / Longitude** | Station coordinates | Set to your monitoring location. Affects weather and tide forecasts. |
| **Cache Expiry** | 21600 s (6 hours) | How long a weather forecast is reused before refetching. |
| **Forecast Days** | 7 | Number of forecast days to request. |
| **Timezone** | auto | Leave as "auto" unless you need a specific timezone. |

After changing the location, use the **Refetch Forecast** button on the Dashboard's weather card to pull fresh data immediately.

### 7.7 SMS Alert Configuration

Choose which risk levels trigger SMS alerts:

- ☐ Receding
- ☐ Alert
- ☑ Alarm *(default on)*
- ☑ Critical *(default on)*

Only checked levels will send SMS messages to active contacts.

### 7.8 Dashboard

| Setting | Default | Notes |
|---------|---------|-------|
| **Host** | 0.0.0.0 | Network interface. *Requires restart.* |
| **Port** | 8000 | Web server port. *Requires restart.* |
| **Auto-Refresh Interval** | 30 seconds | How often the dashboard reloads data. Minimum 5 s. |

### 7.9 Data Collection

| Setting | Default | Notes |
|---------|---------|-------|
| **Water Level Interval** | 60 seconds | How often the sensor is polled. |
| **LoRa Stale-Data Timeout** | 300 seconds (5 min) | If no LoRa data arrives within this window, a warning is logged. |
| **Weather Fetch Interval** | 21600 s (6 hours) | How often weather is refetched automatically. |

### 7.10 Fuzzy Logic Thresholds

Fine-tune the membership function boundaries used by the fuzzy inference engine. These are advanced settings — only adjust them if you understand fuzzy logic and have validated new boundaries.

Four groups are configurable:

- **Water Level (mm)** — Low/Medium/High/Very High boundaries
- **Forecast Rain (mm/day)** — None/Light/Moderate/Heavy boundaries
- **Rate of Rise (mm/hour)** — Negative/Near-Zero/Moderate/Rapid boundaries
- **Tide Level (meters)** — Low/Mid/High/Extreme boundaries

Defaults are documented in the [Glossary](#14-glossary) and the project README.

---

## 8. The Database Page

The **Database** page lets you inspect and export the data the system has collected. Available to all users.

### Features

- **Table list (sidebar)** — All database tables (sensor readings, weather, predictions, alerts, etc.)
- **Table viewer** — Click a table to browse its rows, with pagination
- **Refresh** — Reload the current table view
- **Download Database** — Download the complete SQLite database file for offline analysis or backup

### Typical Uses

- Verify that sensor data is being recorded correctly
- Export data for reports or further analysis
- Investigate historical alerts or predictions

> **Tip:** For routine monitoring, you rarely need this page. It's mainly for verification, reporting, and maintenance.

---

## 9. The Admin Page (Administrators Only)

The **Admin** page is visible only to users with the **admin** role. It has two sections.

### 9.1 Users

Manage dashboard accounts.

**Adding a user:**

1. Enter a **Username**
2. Enter a **Password**
3. Select a **Role**: `Viewer` or `Admin`
4. Click **Add User**

**The users table** lists all accounts with:

| Column | Meaning |
|--------|---------|
| Username | Account name |
| Role | Viewer or Admin |
| Active | Whether the account can sign in |
| Last Login | Timestamp of the most recent sign-in |
| Actions | Edit or Delete buttons |

**Editing a user:** Click the edit action to change the username, password, role, or active status.

**Deleting a user:** Click the delete action. This cannot be undone.

> **Caution:** Do not delete the last remaining administrator account, or you may lock yourself out.

### 9.2 Audit Log

The **Audit Log** records the most recent 100 actions taken on the system, including:

- Sign-ins (and failed sign-in attempts)
- Settings changes
- Alert acknowledgements
- User management actions
- Test SMS sends

Each entry shows: **Time**, **Actor**, **Role**, **Action**, **Target**, **Details**, and **IP address**.

Use this log to review who did what and when — important for accountability during flood response operations.

### 9.3 Acknowledging Alerts

Alerts can also be acknowledged from the [Dashboard's Alerts card](#410-alerts). Acknowledging marks an alert as seen and handled, recording your name and the time.

### 9.4 Restarting the Server

The Settings page has a **Restart Server** button. Use it after changing settings that require a restart (such as Host or Port). The dashboard will be briefly unavailable.

### 9.5 Changing Your Password / Security

- Change the default `admin` password immediately after first installation.
- Use strong, unique passwords for each user.
- Review the Audit Log regularly.
- The dashboard is LAN-only by default; do not expose it to the public internet without additional security (e.g. HTTPS, VPN).

---

## 10. User Accounts & Roles

### Roles

| Capability | Viewer | Admin |
|-----------|:------:|:-----:|
| View dashboard, charts, alerts | ✅ | ✅ |
| View Fuzzy Rules page | ✅ | ✅ |
| Browse / download database | ✅ | ✅ |
| Refresh prediction | ✅ | ✅ |
| Send test SMS alert | ❌ | ✅ |
| Acknowledge alerts | ❌ | ✅ |
| Edit settings | ❌ (read-only) | ✅ |
| Manage alert contacts | ❌ | ✅ |
| Manage users | ❌ | ✅ |
| View audit log | ❌ | ✅ |
| Restart server | ❌ | ✅ |

### Default Account

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin` | Admin |

**Change this immediately after installation.**

### Getting an Account

Contact your system administrator to have an account created for you.

---

## 11. Daily Operating Procedures

### 11.1 Daily Monitoring Checklist

Perform at the start of each shift and periodically throughout:

1. **Sign in** to the dashboard.
2. **Check the Current Status card:**
   - Is the live indicator green and showing "Live"?
   - Is the water level reasonable (not stuck at the same value for hours)?
   - What are the 24h and 48h risk badges showing?
3. **Check System Status:** All four components (LoRa, SMS, Weather API, Prediction Model) should show OK.
4. **Check Sensor Health:** Badge should show OK; no recent gaps.
5. **Review the Alerts card:** Any outstanding alerts? Acknowledge them (admin).
6. **Glance at the 7-Day Forecast:** Does the forecast line approach or cross any threshold in the coming days?
7. **If anything looks wrong,** follow the [Troubleshooting](#12-troubleshooting) steps or notify a supervisor.

### 11.2 Managing Alert Contacts

**Adding a contact (admin):**

1. On the Dashboard, find the **Alert Contacts** card.
2. Click **Add Contact**.
3. Enter the contact's name and phone number (include country code, e.g. `+639…`).
4. Save. The contact is added as active.

**Deactivating a contact (admin):** Toggle the contact's active status off. They remain in the list but stop receiving SMS.

**Testing SMS delivery (admin):**

1. Click **Send Test Message** on the Alert Contacts card (or **Test SMS Alert** on the Current Status card).
2. Confirm recipients received the test message.
3. If not received, check the SMS Module status in System Status and see [Troubleshooting](#12-sms-messages-are-not-sent).

Perform a test send weekly and before any severe-weather event.

### 11.3 Responding to an Alarm or Critical Alert

1. **Confirm** the risk level on the dashboard (check both 24h and 48h badges).
2. **Acknowledge** the alert (admin) so responders know it has been seen.
3. **Verify contacts** were notified (check the Alerts card status and with recipients by phone).
4. **Escalate** per your local flood-response protocol.
5. **Continue monitoring** — the dashboard refreshes automatically. Watch for rising levels and new alerts.
6. **Document** actions taken; the Audit Log records system-side acknowledgements automatically.

### 11.4 Refreshing Predictions Manually

Predictions normally run automatically every 5 minutes. To force a fresh prediction (for example after heavy rain just started):

1. Click **Refresh Prediction** on the Current Status card.
2. Wait a few seconds; the risk badges and charts update.

### 11.5 Forcing a Weather Refetch (Admin)

If the weather forecast seems out of date:

1. On the **Current Weather & Rainfall** card, click **Refetch Forecast**.
2. The system pulls a fresh 7-day forecast immediately (bypassing the 6-hour cache).

---

## 12. Troubleshooting

### "Waiting for data…" / No water level readings

- Check the **System Status** card — is the LoRa Module showing OK?
- Check the **Sensor Health** card for gaps or staleness.
- Verify the remote sensor is powered and within radio range.
- Ensure the LoRa Receiver toggle is enabled in Settings (admin).
- If persistent, the hardware may need attention — notify a technician.

### Dashboard won't load

- Confirm you're on a private network the station is connected to: its home LAN, or the same phone hotspot in the field (see the access table in Section 1).
- Check the station's IP address and port (default `:8000`).
- Try a different browser or device.
- Ask an administrator to verify the server is running.

### Risk badges show "—" or an old timestamp

- The prediction may not have run yet. Click **Refresh Prediction**.
- If it persists, the Prediction Model may have failed to load — check System Status. The model file may be missing or corrupted; a technician should re-deploy it.

### SMS messages are not sent

- Check that the **SMS Module** shows OK in System Status.
- Confirm **SMS Handler** is enabled in Settings (admin).
- Confirm at least one contact is **active**.
- Confirm the risk level is one of the configured **alert risk levels** (default: Alarm and Critical).
- Remember the **cooldown** (default 30 min) — a recent alert may be blocking a new one.
- Use **Test SMS Alert** to isolate the problem. If the test fails, check the SIM card, antenna, and cellular signal at the station.

### Weather data is stale or wrong

- Check that the **Weather API** shows OK in System Status.
- Verify internet connectivity at the station.
- Check that the **Latitude/Longitude** in Settings match your location.
- Use **Refetch Forecast** (admin) to pull fresh data immediately.

### Settings won't save

- Confirm you're signed in as an **admin**. Viewers cannot edit settings.
- Check for validation errors (e.g. out-of-range values).
- If the page seems stuck, sign out and back in, then retry.

### I'm locked out / forgot password

- Contact another administrator to reset your password on the Admin page.
- If no administrator can sign in, a technician can restore access via the default account or database on the station itself.

### The dashboard looks broken or unstyled

- Force a hard refresh: **Ctrl + Shift + R** (Windows/Linux) or **Cmd + Shift + R** (Mac).
- This clears a cached stylesheet and reloads the correct one.

---

## 13. Frequently Asked Questions

**Q: How often does the water level update?**
A: Every minute via the LoRa sensor. The dashboard itself refreshes every 30 seconds by default.

**Q: How often is the flood prediction updated?**
A: Automatically every 5 minutes. You can also trigger one manually with **Refresh Prediction**.

**Q: What's the difference between the 24h and 48h horizons?**
A: 24h is the risk for today (using today's weather forecast). 48h is the risk for tomorrow (using tomorrow's forecast). A higher 48h badge warns of worsening conditions.

**Q: Why is the risk level different from the raw water level I'd expect?**
A: The risk level combines five inputs (water level, rate of rise, forecast rain, tide, and the Random Forest propensity) via fuzzy logic. A moderate water level can still produce a high risk if rain is heavy and the tide is high. See the Fuzzy Rules page for the exact logic.

**Q: Can I access the dashboard from my phone?**
A: Yes — from the station's home LAN, or from the phone hotspot it auto-joins in the field. It is never exposed to the public internet.

**Q: Can two people be signed in at once?**
A: Yes. Each user signs in with their own account; sessions are independent.

**Q: Who receives SMS alerts?**
A: All **active** contacts in the Alert Contacts list, when the risk level matches one of the configured alert risk levels (default: Alarm and Critical).

**Q: How do I stop SMS alerts temporarily?**
A: An admin can disable the **SMS Handler** in Settings → Module Control, or deactivate individual contacts. Re-enable when ready.

**Q: What do I do if the system shows Critical?**
A: Follow your emergency response protocol immediately. The dashboard is a decision aid — always follow official PAGASA warnings and local authority instructions.

---

## 14. Glossary

| Term | Definition |
|------|-----------|
| **LoRa** | Long-range low-power radio technology used to receive sensor data from the remote water-level sensor (RFM95W module, 915 MHz). |
| **RFM95W** | The LoRa radio module installed in the station for receiving sensor transmissions. |
| **A7608e-H** | The cellular modem used to send SMS alerts. |
| **Rate of Rise (RoR)** | How fast the water level is changing, in mm per hour. A rapid rise is a flood warning sign. |
| **Random Forest (RF)** | A machine-learning model that classifies flood propensity (Low/Medium/High) from 8 features: 1-day, 3-day, and 7-day rainfall, consecutive rain days, max/min temperature, and max/min tide. |
| **Fuzzy Logic** | A rule-based decision engine (20 rules) that combines water level, rate of rise, forecast rain, tide, and RF propensity into a final risk level (Receding/Alert/Alarm/Critical). |
| **RF Propensity** | The Random Forest model's output: Low, Medium, or High flood propensity. |
| **Risk Horizon** | The prediction window: 24 hours (today) or 48 hours (tomorrow). |
| **Receding** | Risk level indicating the water level is falling after a high-water period. |
| **Alert / Alarm / Critical** | Increasingly severe flood risk levels (Yellow / Orange / Red). |
| **Open-Meteo** | The free weather and marine (tide) data API used for forecasts. |
| **Rain Tip** | One tip of the tipping-bucket rain gauge (default 0.2 mm of rainfall). |
| **Critical Level** | The water level set as 100% risk (default 2.0 m). Configured after a hydrological survey. |
| **Cooldown** | The minimum time (default 30 min) between SMS alerts to prevent message flooding. |
| **Audit Log** | A record of system actions (sign-ins, settings changes, acknowledgements) for accountability. |
| **Viewer / Admin** | The two user roles. Admins can change settings, manage users/contacts, and acknowledge alerts; Viewers have read-only access. |

---

## Document Information

| | |
|---|---|
| **Manual version** | 1.0 |
| **Last updated** | October 2026 |
| **Applies to** | River Monitor System (Raspberry Pi 5 deployment) |
| **Related documentation** | `README.md` (technical setup), `DATABASE_SCHEMA.md`, `SYSTEM_FLOWCHART.md` |

For technical installation, hardware wiring, and model training, see the project `README.md`. For questions about this manual, contact your system administrator or project supervisor.

---

*This system is a decision aid for flood monitoring. Always follow official weather service warnings and local emergency authority instructions.*
