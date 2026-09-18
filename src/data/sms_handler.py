"""
SMS Handler for River Monitor System
Handles A7608e-H module communication for SMS alerts (send-only).

The sensor node is LoRa-only (no SMS module), so the SMS module on the
Raspberry Pi is used solely to send alert messages to configured phone
numbers. It does not request or receive data from the sensor.
"""

import time
import serial
import threading
from datetime import datetime

from src.config import (
    SMS_ENABLED, SMS_UART_PORT, SMS_BAUD_RATE, SMS_TIMEOUT,
    SMS_ALERT_TEMPLATE, SMS_ALERT_RISK_LEVELS, SMS_ALERT_COOLDOWN_MINUTES
)
from src.data.database import (
    insert_alert, update_alert_status,
    get_active_alert_phone_numbers
)


# Module-level alert cooldown (SMSHandler is instantiated per use, so the
# state must live at module scope to persist across sends).
_RISK_SEVERITY = {'receding': 0, 'alert': 1, 'alarm': 2, 'critical': 3}
_alert_state_lock = threading.Lock()
_last_alert_at = None
_last_alert_severity = -1


def _cooldown_blocks(risk_key: str) -> bool:
    """True if a same-or-lower-severity alert was sent within the cooldown window."""
    global _last_alert_at, _last_alert_severity
    with _alert_state_lock:
        if _last_alert_at is None:
            return False
        elapsed = (datetime.now() - _last_alert_at).total_seconds()
        severity = _RISK_SEVERITY.get(risk_key, 0)
        return elapsed < SMS_ALERT_COOLDOWN_MINUTES * 60 and severity <= _last_alert_severity


def _mark_sent(risk_key: str):
    """Record that an alert was sent so the cooldown can suppress repeats."""
    global _last_alert_at, _last_alert_severity
    with _alert_state_lock:
        _last_alert_at = datetime.now()
        _last_alert_severity = _RISK_SEVERITY.get(risk_key, 0)


class SMSHandler:
    """A7608e-H SMS module handler"""
    
    def __init__(self):
        self.serial_port = None
        self.last_sms_time = None
        
        if not SMS_ENABLED:
            print("SMS module is DISABLED in config (SMS_ENABLED=False)")
            self.enabled = False
            return
        
        self.enabled = True
        self.connect()
    
    def connect(self, max_retries: int = 3) -> bool:
        """Connect to the SMS module"""
        if not self.enabled:
            return False
        
        for attempt in range(max_retries):
            try:
                self.serial_port = serial.Serial(
                    port=SMS_UART_PORT,
                    baudrate=SMS_BAUD_RATE,
                    timeout=SMS_TIMEOUT,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS
                )
                
                # Test connection
                if self.send_at_command("AT", expected_response="OK"):
                    print("SMS module connected successfully")
                    return True
                else:
                    self.serial_port.close()
                    self.serial_port = None
                    
            except serial.SerialException as e:
                print(f"Failed to connect to SMS module (attempt {attempt + 1}): {e}")
                if self.serial_port:
                    self.serial_port.close()
                    self.serial_port = None
                time.sleep(1)
        
        print("Failed to connect to SMS module after all attempts")
        return False
    
    def send_at_command(self, command: str, expected_response: str = None, 
                        timeout: float = SMS_TIMEOUT) -> bool:
        """Send AT command and check response"""
        if not self.serial_port or not self.serial_port.is_open:
            if not self.connect():
                return False
        
        try:
            # Clear any existing data
            self.serial_port.reset_input_buffer()
            
            # Send command
            self.serial_port.write((command + "\r\n").encode())
            
            # Read response
            start_time = time.time()
            response = ""
            
            while time.time() - start_time < timeout:
                if self.serial_port.in_waiting:
                    line = self.serial_port.readline().decode().strip()
                    response += line + "\n"
                    if expected_response and expected_response in line:
                        return True
                    if "ERROR" in line:
                        return False
                time.sleep(0.1)
            
            return expected_response is None or expected_response in response
            
        except Exception as e:
            print(f"Error sending AT command: {e}")
            return False
    
    def initialize_module(self) -> bool:
        """Initialize the SMS module"""
        commands = [
            ("AT", "OK"),
            ("AT+CPIN?", "READY"),  # Check SIM card
            ("AT+CREG?", "OK"),     # Check network registration
            ("AT+CMGF=1", "OK")     # Set SMS to text mode
        ]
        
        for cmd, expected in commands:
            if not self.send_at_command(cmd, expected):
                print(f"Failed to execute: {cmd}")
                return False
        
        print("SMS module initialized")
        return True
    
    def send_sms(self, phone_number: str, message: str) -> bool:
        """Send an SMS message"""
        if not self.initialize_module():
            return False
        
        # Escape quotes in message
        escaped_message = message.replace('"', '\\"')
        
        # Send SMS command
        command = f'AT+CMGS="{phone_number}"'
        if not self.send_at_command(command, expected_response=">"):
            print("Failed to start SMS sending")
            return False
        
        # Send message and Ctrl+Z
        self.serial_port.write((escaped_message + "\x1A").encode())
        
        # Wait for confirmation
        time.sleep(2)
        if self.send_at_command("", expected_response="OK", timeout=10):
            print(f"SMS sent to {phone_number}: {message}")
            return True
        else:
            print(f"Failed to send SMS to {phone_number}")
            return False
    
    def send_alert(self, risk_level: str, water_level_m: float, forecast_change: float) -> bool:
        """Send SMS alerts for high risk levels"""
        risk_key = (risk_level or '').strip().lower()
        if risk_key not in [str(r).lower() for r in SMS_ALERT_RISK_LEVELS]:
            return False

        message = SMS_ALERT_TEMPLATE.format(
            risk_level=risk_key.upper(),
            water_level=water_level_m,
            forecast_change=forecast_change
        )

        # Get phone numbers from database based on risk level
        phone_numbers = get_active_alert_phone_numbers(risk_key)
        
        if not phone_numbers:
            print(f"No active contacts configured for {risk_level} alerts")
            return False
        
        # Record alert in database
        alert_id = insert_alert(
            datetime.now(),
            risk_key.capitalize(),
            water_level_m,
            message,
            ",".join(phone_numbers),
            "pending"
        )
        
        # Send to all phone numbers
        success = True
        for phone_number in phone_numbers:
            if self.send_sms(phone_number, message):
                print(f"Alert sent to {phone_number}")
            else:
                success = False
                update_alert_status(alert_id, "failed")
                break
        
        if success:
            update_alert_status(alert_id, "sent")
        
        return success
    
    def cleanup(self):
        """Clean up serial connection"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()


def send_alert_sms(risk_level: str, water_level_m: float, forecast_change: float):
    """Send SMS alert for high risk levels"""
    if not SMS_ENABLED:
        print("Alert SMS skipped: SMS module is DISABLED in config")
        return

    risk_key = (risk_level or '').strip().lower()
    if risk_key not in [str(r).lower() for r in SMS_ALERT_RISK_LEVELS]:
        print(f"Alert SMS skipped: {risk_level} not in configured alert levels")
        return

    if _cooldown_blocks(risk_key):
        print(f"Alert SMS suppressed by cooldown ({risk_key})")
        return

    handler = SMSHandler()
    try:
        if handler.send_alert(risk_key, water_level_m, forecast_change):
            _mark_sent(risk_key)
            print(f"Alert SMS sent for {risk_key} risk level")
        else:
            print(f"Failed to send alert SMS for {risk_key}")
    finally:
        handler.cleanup()


def test_alert_sms():
    """Test SMS alert system with a test message"""
    if not SMS_ENABLED:
        print("Test alert skipped: SMS module is DISABLED in config")
        return False
    
    handler = SMSHandler()
    try:
        # Get all active contacts for testing
        from src.data.database import get_all_alert_contacts
        contacts = get_all_alert_contacts(active_only=True)
        phone_numbers = [c['phone_number'] for c in contacts]
        
        if not phone_numbers:
            print("No active contacts configured for test")
            return False
        
        message = "[TEST] River Monitor System - Test Alert"
        success = True
        for phone_number in phone_numbers:
            if handler.send_sms(phone_number, message):
                print(f"Test alert sent to {phone_number}")
            else:
                success = False
                print(f"Failed to send test alert to {phone_number}")
        
        return success
    finally:
        handler.cleanup()


if __name__ == "__main__":
    # Test SMS functionality
    if not SMS_ENABLED:
        print("SMS module is DISABLED in config. Skipping.")
    else:
        handler = SMSHandler()
        try:
            if handler.connect():
                print("Testing SMS module...")
                # Test sending (uncomment to test)
                # handler.send_sms("+639123456789", "Test message from River Monitor")
        finally:
            handler.cleanup()