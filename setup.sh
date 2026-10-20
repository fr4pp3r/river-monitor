#!/bin/bash

# River Monitor System Setup Script
# Run this on Raspberry Pi 5 to set up the system

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please do not run this script as root. Run as regular user.${NC}"
    exit 1
fi

# Check if on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model; then
    echo -e "${YELLOW}Warning: This script is designed for Raspberry Pi. Continuing anyway...${NC}"
fi

# Function to print section headers
print_section() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Run an apt command but do NOT let a failure abort the script (set -e safe).
# System package failures (e.g. camera/multimedia stack) should not block
# the parts of the setup that actually matter for this project.
apt_nonfatal() {
    if sudo apt-get "$@"; then
        echo -e "${GREEN}apt-get $1 completed successfully${NC}"
    else
        echo -e "${RED}Warning: apt-get $1 reported errors (exit code $?).${NC}"
        echo -e "${YELLOW}Continuing setup anyway — many system packages are unrelated to the river monitor and can be skipped.${NC}"
    fi
}

# ---------------------------------------------------------------------------
# SYSTEM UPDATE / UPGRADE  (OPTIONAL — SKIPPED BY DEFAULT)
# ---------------------------------------------------------------------------
# By default we do NOT run `apt update` / `apt upgrade`. Doing a full system
# upgrade on a Raspberry Pi can be risky: if it is interrupted or a
# camera/multimedia package (ffmpeg, rpicam-apps, gstreamer, ...) fails to
# configure mid-way, a reboot can leave the OS unbootable.
#
# The river monitor does NOT need these packages, and a fresh Raspberry Pi OS
# already ships everything required (python3, pip, etc.). So we skip the
# upgrade entirely unless you explicitly opt in.
#
# To enable it, run setup with:   ./setup.sh --update
# ---------------------------------------------------------------------------

SKIP_SYSTEM_UPDATE=1
PHONE_HOTSPOT_SSID=""
PHONE_HOTSPOT_PSK=""
PHONE_HOTSPOT_PSK_SET=0
PHONE_HOTSPOT_CONFIGURED=0
PHONE_HOTSPOT_DEFAULT_SSID="FLAIRE2026"
PHONE_HOTSPOT_DEFAULT_PSK="flaire2026"

# Parse flags. Value-taking flags are given as --flag=value (so values can
# be empty); bare --phone-hotspot always means the default SSID below.
for arg in "$@"; do
    case "$arg" in
        --update)
            SKIP_SYSTEM_UPDATE=0
            ;;
        --phone-hotspot)
            PHONE_HOTSPOT_SSID="$PHONE_HOTSPOT_DEFAULT_SSID"
            ;;
        --phone-hotspot=*)
            PHONE_HOTSPOT_SSID="${arg#--phone-hotspot=}"
            ;;
        --phone-hotspot-psk=*)
            PHONE_HOTSPOT_PSK="${arg#--phone-hotspot-psk=}"
            PHONE_HOTSPOT_PSK_SET=1
            ;;
        *)
            echo -e "${YELLOW}Note: ignoring unknown option: $arg${NC}"
            ;;
    esac
done

# A bare --phone-hotspot-psk=<PSK> without --phone-hotspot also turns the
# feature on, using the default SSID.
if [ -z "$PHONE_HOTSPOT_SSID" ] && [ "$PHONE_HOTSPOT_PSK_SET" -eq 1 ]; then
    PHONE_HOTSPOT_SSID="$PHONE_HOTSPOT_DEFAULT_SSID"
fi

if [ "$SKIP_SYSTEM_UPDATE" -eq 1 ]; then
    echo -e "${YELLOW}Skipping system update/upgrade.${NC}"
    echo -e "${YELLOW}To run it, re-run this script with: ./setup.sh --update${NC}"
    echo -e "${YELLOW}(Only do this when you can afford to reboot after it completes.)${NC}"
else
    print_section "Updating System Packages"

    # Repair any broken package state left over from a previous/interrupted upgrade.
    # This is the common cause of "E: Sub-process /usr/bin/dpkg returned an error code (1)".
    echo -e "${YELLOW}Repairing broken package state (dpkg --configure -a)...${NC}"
    apt_nonfatal --fix-broken install
    apt_nonfatal -f install

    echo -e "${YELLOW}Updating apt package lists...${NC}"
    apt_nonfatal update

    echo -e "${YELLOW}Upgrading installed packages...${NC}"
    apt_nonfatal upgrade
fi

# Install required system packages
print_section "Installing System Dependencies"
PACKAGES=(
    "python3-pip"
    "python3-venv"
    "python3-dev"
    "build-essential"
    "pkg-config"
    "git"
    "spidev"
    "libatlas-base-dev"
    "libjpeg-dev"
    "libpng-dev"
    "libfreetype6-dev"
    "zlib1g-dev"
    "libopenblas-dev"
    "liblapack-dev"
)

echo -e "${YELLOW}Installing packages: ${PACKAGES[*]}${NC}"
apt_nonfatal install -y "${PACKAGES[@]}"

# Enable SPI and UART
print_section "Enabling Hardware Interfaces"

# Check if SPI is already enabled
if ! grep -q "^dtparam=spi=on" /boot/config.txt; then
    echo -e "${YELLOW}Enabling SPI...${NC}"
    echo "dtparam=spi=on" | sudo tee -a /boot/config.txt
else
    echo -e "${GREEN}SPI is already enabled${NC}"
fi

# Check if UART is already enabled
if ! grep -q "^enable_uart=1" /boot/config.txt; then
    echo -e "${YELLOW}Enabling UART...${NC}"
    echo "enable_uart=1" | sudo tee -a /boot/config.txt
else
    echo -e "${GREEN}UART is already enabled${NC}"
fi

# Enable serial console (for SMS module)
if ! grep -q "^dtoverlay=disable-bt" /boot/config.txt; then
    echo -e "${YELLOW}Disabling Bluetooth to free UART...${NC}"
    echo "dtoverlay=disable-bt" | sudo tee -a /boot/config.txt
fi

# Add user to necessary groups
print_section "Configuring User Permissions"
USERNAME=$(whoami)

if ! id -nG "$USERNAME" | grep -q "gpio"; then
    echo -e "${YELLOW}Adding user to gpio group...${NC}"
    sudo usermod -aG gpio "$USERNAME"
else
    echo -e "${GREEN}User is already in gpio group${NC}"
fi

if ! id -nG "$USERNAME" | grep -q "spi"; then
    echo -e "${YELLOW}Adding user to spi group...${NC}"
    sudo usermod -aG spi "$USERNAME"
else
    echo -e "${GREEN}User is already in spi group${NC}"
fi

if ! id -nG "$USERNAME" | grep -q "dialout"; then
    echo -e "${YELLOW}Adding user to dialout group (for serial ports)...${NC}"
    sudo usermod -aG dialout "$USERNAME"
else
    echo -e "${GREEN}User is already in dialout group${NC}"
fi

# Create project directory
print_section "Setting Up Project Directory"
PROJECT_DIR="$(pwd)"

echo -e "${YELLOW}Project directory: $PROJECT_DIR${NC}"

# Create data directories
mkdir -p "$PROJECT_DIR/data/models"
mkdir -p "$PROJECT_DIR/data/weather_cache"

# Create Python virtual environment
print_section "Creating Python Virtual Environment"

if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv "$PROJECT_DIR/venv"
else
    echo -e "${GREEN}Virtual environment already exists${NC}"
fi

# Activate virtual environment and install dependencies
print_section "Installing Python Dependencies"

# Activate venv
source "$PROJECT_DIR/venv/bin/activate"

# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    echo -e "${YELLOW}Installing Python packages...${NC}"
    python -m pip install --no-cache-dir -r "$PROJECT_DIR/requirements.txt"
else
    echo -e "${RED}requirements.txt not found!${NC}"
    exit 1
fi

# Initialize database
print_section "Initializing Database"

echo -e "${YELLOW}Creating database...${NC}"
python "$PROJECT_DIR/src/data/database.py"

# Create systemd service for automatic startup
print_section "Creating Systemd Service"

SERVICE_FILE="/etc/systemd/system/river-monitor.service"

if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${YELLOW}Creating systemd service...${NC}"
    
    # Create service file
    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=River Monitor System
After=network.target
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
User=$USERNAME
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin:$PATH"
Environment=PYTHONUNBUFFERED=1
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/src/web/main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Enable and start service
    echo -e "${YELLOW}Reloading systemd...${NC}"
    sudo systemctl daemon-reload
    
    echo -e "${YELLOW}Enabling service to start on boot...${NC}"
    sudo systemctl enable river-monitor.service
    
    echo -e "${GREEN}Systemd service created successfully!${NC}"
    echo -e "${YELLOW}To start the service: sudo systemctl start river-monitor${NC}"
    echo -e "${YELLOW}To check status: sudo systemctl status river-monitor${NC}"
else
    echo -e "${GREEN}Systemd service already exists${NC}"
fi

# Create cron job for weather data fetching
print_section "Setting Up Weather Data Cron Job"

CRON_JOB="0 */6 * * * $PROJECT_DIR/venv/bin/python $PROJECT_DIR/src/data/weather_fetcher.py"

if ! crontab -l 2>/dev/null | grep -q "weather_fetcher.py"; then
    echo -e "${YELLOW}Adding cron job for weather data...${NC}"
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo -e "${GREEN}Cron job added successfully!${NC}"
else
    echo -e "${GREEN}Cron job already exists${NC}"
fi

# ---------------------------------------------------------------------------
# REMOTE ACCESS (mDNS; opt-in phone hotspot autoconnect follows below)
# ---------------------------------------------------------------------------
# mDNS (avahi-daemon) means devices on the same local link can reach the Pi
# by hostname, http://<hostname>.local:8000, without knowing its IP. This
# works on every network the Pi joins — its home LAN, another site, or the
# phone hotspot it can auto-connect to (see the next section) — and unlike
# a fixed LAN IP it does not change when the network changes.
# The install is idempotent, so it runs on every setup.

print_section "Configuring Remote Access"

echo -e "${YELLOW}Installing avahi-daemon (mDNS)...${NC}"
apt_nonfatal install -y avahi-daemon

if sudo systemctl enable --now avahi-daemon; then
    echo -e "${GREEN}mDNS enabled — reachable as http://$(hostname).local:8000 on every network the Pi joins${NC}"
else
    echo -e "${YELLOW}Warning: could not enable avahi-daemon; mDNS names may not resolve.${NC}"
fi

# ---------------------------------------------------------------------------
# PHONE HOTSPOT AUTOCONNECT (opt-in)
# ---------------------------------------------------------------------------
# Run with one of:
#   ./setup.sh --phone-hotspot
#       uses the project default SSID (FLAIRE2026) and default WPA2 PSK
#       (flaire2026). The PSK is committed in this repo, so it provides
#       convenience rather than secrecy — rotate via --phone-hotspot-psk=.
#   ./setup.sh --phone-hotspot=<SSID>            (overrides the SSID only)
#   ./setup.sh --phone-hotspot=<SSID> --phone-hotspot-psk=<PSK>
#   ./setup.sh --phone-hotspot --phone-hotspot-psk=   (explicit OPEN network;
#       see the evil-twin warning printed below)
# Creates an idempotent NetworkManager profile (name: "phone-hotspot") that
# autoconnects whenever the phone hotspot is in range, giving the Pi internet
# in the field (weather data stays current) and putting it on the hotspot's
# network, where the dashboard is reachable via mDNS or the hotspot LAN IP.

HOTSPOT_PSK="$PHONE_HOTSPOT_PSK"
HOTSPOT_OPEN=0
HOTSPOT_PSK_IS_DEFAULT=0
if [ "$PHONE_HOTSPOT_PSK_SET" -eq 1 ] && [ -z "$PHONE_HOTSPOT_PSK" ]; then
    HOTSPOT_OPEN=1
elif [ -z "$PHONE_HOTSPOT_PSK" ]; then
    HOTSPOT_PSK="$PHONE_HOTSPOT_DEFAULT_PSK"
    HOTSPOT_PSK_IS_DEFAULT=1
fi

if [ -n "$PHONE_HOTSPOT_SSID" ]; then
    print_section "Phone Hotspot Autoconnect"

    if command_exists nmcli; then
        HOTSPOT_CON_NAME="phone-hotspot"
        HOTSPOT_FAILED=0

        # Create the profile once, or update its SSID on re-runs.
        if sudo nmcli connection show "$HOTSPOT_CON_NAME" >/dev/null 2>&1; then
            echo -e "${YELLOW}Profile '$HOTSPOT_CON_NAME' exists — updating SSID to '$PHONE_HOTSPOT_SSID'...${NC}"
            sudo nmcli connection modify "$HOTSPOT_CON_NAME" 802-11-wireless.ssid "$PHONE_HOTSPOT_SSID" || HOTSPOT_FAILED=1
        else
            echo -e "${YELLOW}Creating profile '$HOTSPOT_CON_NAME' for SSID '$PHONE_HOTSPOT_SSID'...${NC}"
            sudo nmcli connection add type wifi ifname wlan0 con-name "$HOTSPOT_CON_NAME" ssid "$PHONE_HOTSPOT_SSID" || HOTSPOT_FAILED=1
        fi

        if [ "$HOTSPOT_FAILED" -eq 0 ]; then
            # Security: explicit on each run, so re-runs cleanly switch
            # between WPA2 and open (clears any prior stored key-mgmt).
            if [ "$HOTSPOT_OPEN" -eq 1 ]; then
                echo -e "${YELLOW}Setting profile to open (no security)...${NC}"
                sudo nmcli connection modify "$HOTSPOT_CON_NAME" 802-11-wireless-security.key-mgmt "" || HOTSPOT_FAILED=1
                HOTSPOT_MODE="open"
            else
                echo -e "${YELLOW}Securing profile with WPA2-PSK...${NC}"
                sudo nmcli connection modify "$HOTSPOT_CON_NAME" 802-11-wireless-security.key-mgmt wpa-psk 802-11-wireless-security.psk "$HOTSPOT_PSK" || HOTSPOT_FAILED=1
                HOTSPOT_MODE="WPA2-PSK"
            fi

            # Autoconnect when in range; priority 20 makes the Pi roam to the
            # phone hotspot ahead of lower-priority networks.
            sudo nmcli connection modify "$HOTSPOT_CON_NAME" connection.autoconnect yes connection.autoconnect-priority 20 || HOTSPOT_FAILED=1
        fi

        if [ "$HOTSPOT_FAILED" -eq 0 ]; then
            PHONE_HOTSPOT_CONFIGURED=1
            echo -e "${GREEN}Phone hotspot autoconnect configured${NC}"
            echo -e "  SSID:     $PHONE_HOTSPOT_SSID ($HOTSPOT_MODE)"
            echo -e "  Priority: 20 — the Pi joins it whenever the hotspot is in range"
            echo ""
            echo -e "${YELLOW}One-radio caveat: wlan0 is the Pi's only WiFi radio. While joined to the${NC}"
            echo -e "${YELLOW}phone hotspot, the Pi is NOT on any other WiFi (AccessPopup, home LAN).${NC}"
            echo -e "${YELLOW}Reach the dashboard then from a device connected to the same phone${NC}"
            echo -e "${YELLOW}hotspot — via its LAN IP or the mDNS name.${NC}"
            if [ "$HOTSPOT_OPEN" -eq 1 ]; then
                echo ""
                echo -e "${RED}Security warning (open network): unsecured WiFi invites both accidental${NC}"
                echo -e "${RED}joins and evil-twin spoofing — anyone in range can broadcast the same SSID.${NC}"
                echo -e "${RED}Prefer a PSK: re-run with --phone-hotspot-psk=<PSK>.${NC}"
            elif [ "$HOTSPOT_PSK_IS_DEFAULT" -eq 1 ]; then
                echo ""
                echo -e "${YELLOW}Security note: the default WPA2 PSK (flaire2026) is committed in this${NC}"
                echo -e "${YELLOW}repository's docs, so it is convenience, not secrecy. Rotate it when${NC}"
                echo -e "${YELLOW}practical: re-run with --phone-hotspot-psk=<PSK>.${NC}"
            fi
        else
            echo -e "${RED}Warning: the phone hotspot profile could not be fully configured.${NC}"
            echo -e "${YELLOW}Check the nmcli error above, fix it, then re-run:${NC}"
            echo -e "${YELLOW}  ./setup.sh --phone-hotspot=\"$PHONE_HOTSPOT_SSID\"${NC}"
        fi
    else
        echo -e "${YELLOW}Warning: nmcli not found — this Raspberry Pi OS build does not use${NC}"
        echo -e "${YELLOW}NetworkManager (pre-Bookworm). Configure the hotspot manually instead:${NC}"
        echo -e "${YELLOW}add a network block to /etc/wpa_supplicant/wpa_supplicant.conf${NC}"
        if [ "$HOTSPOT_OPEN" -eq 1 ]; then
            echo -e "${YELLOW}   network={ ssid=\"$PHONE_HOTSPOT_SSID\" key_mgmt=NONE }${NC}"
        else
            echo -e "${YELLOW}   network={ ssid=\"$PHONE_HOTSPOT_SSID\" psk=\"$HOTSPOT_PSK\" }${NC}"
        fi
        echo -e "${YELLOW}Continuing setup without the hotspot profile.${NC}"
    fi
fi

# Summary
print_section "Setup Complete!"

echo -e "${GREEN}River Monitor System has been set up successfully!${NC}\n"

echo "Next Steps:"
echo "1. Configure your settings in src/config.py:"
echo "   - Update ALERT_PHONE_NUMBERS with actual phone numbers"
echo "   - Adjust CRITICAL_LEVEL_M based on your hydrological survey"
echo "   - Verify WEATHER_LATITUDE and WEATHER_LONGITUDE for your location"
echo ""
echo "2. Train the AI model (run on a PC with more resources):"
echo "   python src/model/train.py --mode new --csv <training_data.csv> --output data/models/rf_model.pkl"
echo "   (Training CSV must have columns: R1, R3, R7, rainy_days, TMAX, TMIN, TideMax, target)"
echo ""
echo "4. Copy the trained model to the Raspberry Pi:"
echo "   - Copy data/models/rf_model.pkl and data/models/scaler.pkl to the Pi"
echo ""
echo "5. Run database migration:"
echo "   python migrate_db.py"
echo ""
echo "6. Start the system:"
echo "   - Manually: python src/web/main.py"
echo "   - As service: sudo systemctl start river-monitor"
echo ""
echo "7. Access the dashboard (any of these):"
echo "   - mDNS hostname:  http://$(hostname).local:8000  (same name on every network the Pi joins)"
echo "   - LAN IP:         http://<raspberry-pi-ip>:8000"
if [ "$PHONE_HOTSPOT_CONFIGURED" -eq 1 ]; then
    echo "   Phone hotspot autoconnect: will join '$PHONE_HOTSPOT_SSID' when in range."
    echo "   (One WiFi radio: while joined, the Pi is not on other WiFi such as AccessPopup.)"
fi
echo ""
echo "8. Test the LoRa receiver (in a separate terminal):"
echo "   python src/data/lora_receiver.py"
echo ""
echo "9. Test the SMS handler (in a separate terminal):"
echo "   python src/data/sms_handler.py"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Setup finished!${NC}"
echo -e "${GREEN}========================================${NC}\n"

# Deactivate virtual environment
deactivate