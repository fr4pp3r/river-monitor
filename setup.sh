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

# Update system
print_section "Updating System Packages"

# Repair any broken package state left over from a previous/interrupted upgrade.
# This is the common cause of "E: Sub-process /usr/bin/dpkg returned an error code (1)".
echo -e "${YELLOW}Repairing broken package state (dpkg --configure -a)...${NC}"
apt_nonfatal --fix-broken install
apt_nonfatal -f install

echo -e "${YELLOW}Updating apt package lists...${NC}"
apt_nonfatal update

echo -e "${YELLOW}Upgrading installed packages...${NC}"
# NOTE: Use a non-fatal upgrade. On Raspberry Pi OS the camera/multimedia
# packages (ffmpeg, rpicam-apps, gstreamer, etc.) sometimes fail to configure.
# These are NOT needed by the river monitor, so we warn and continue instead
# of stopping the whole setup.
apt_nonfatal upgrade

# Install required system packages
print_section "Installing System Dependencies"
PACKAGES=(
    "python3-pip"
    "python3-venv"
    "python3-dev"
    "git"
    "spidev"
    "libatlas-base-dev"
    "libjpeg-dev"
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
    python -m pip install -r "$PROJECT_DIR/requirements.txt"
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

[Service]
Type=simple
User=$USERNAME
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin:$PATH"
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/src/web/main.py
Restart=always
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

CRON_JOB="*/6 * * * * $PROJECT_DIR/venv/bin/python $PROJECT_DIR/src/data/weather_fetcher.py"

if ! crontab -l 2>/dev/null | grep -q "weather_fetcher.py"; then
    echo -e "${YELLOW}Adding cron job for weather data...${NC}"
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo -e "${GREEN}Cron job added successfully!${NC}"
else
    echo -e "${GREEN}Cron job already exists${NC}"
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
echo "7. Access the dashboard:"
echo "   - Open a browser and go to: http://<raspberry-pi-ip>:8000"
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