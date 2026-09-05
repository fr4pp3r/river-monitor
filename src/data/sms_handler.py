"""
SMS Handler for River Monitor System
Handles A7608e-H module communication for SMS fallback and alerts
"""

import time
import serial
from datetime import datetime
from typing import List, Optional

from src.config import (
    SMS_UART_PORT, SMS_BAUD_RATE, SMS_TIMEOUT,
    ALERT_PHONE_NUMBERS, SMS_ALERT_TEMPLATE, SMS_ALERT_RISK_LEVELS,
    WATER_LEVEL_INTERVAL
)
from src.data.database import (
    insert_water_level, get_latest_water_level,
    insert_alert, update_alert_status, get_recent_alerts
)


class SMSHandler:
    """A7608e-H SMS module handler"""
    
    def __init__(self):
        self.serial_port = None
        self.last_sms_time = None
        self.connect()
    
    def connect(self, max_retries: int = 3) -> bool:
        """Connect to the SMS module"""
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
            ("AT+CMGF=1", "OK"),    # Set SMS to text mode
            ("AT+CNMI=2,2,0,0,0", "OK")  # Configure SMS storage
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
    
    def read_sms(self) -> Optional[str]:
        """Read the latest SMS message (for fallback data collection)"""
        if not self.initialize_module():
            return None
        
        # List messages
        if not self.send_at_command("AT+CMGL="ALL"", expected_response="+CMGL:"):
            return None
        
        # Read response (this is simplified - actual parsing would be more complex)
        time.sleep(1)
        response = ""
        while self.serial_port.in_waiting:
            response += self.serial_port.readline().decode()
        
        # Parse response to extract message
        # This is a simplified parser - actual implementation would need to handle
        # the full +CMGL response format
        if "+CMGL:" in response:
            # Find the message content (after the last quote)
            parts = response.split('"')
            if len(parts) >= 3:
                message = parts[-2]  # Message is between quotes
                return message
        
        return None
    
    def parse_sms_distance(self, message: str) -> Optional[float]:
        """Parse distance from SMS message"""
        # Expected format: "DIST:<value>" or similar
        if "DIST:" in message:
            try:
                distance_str = message.split("DIST:")[1].split()[0]
                return float(distance_str)
            except (ValueError, IndexError):
                return None
        return None
    
    def request_sensor_data(self) -> bool:
        """Request sensor data via SMS (for fallback)"""
        # This would send a command to the remote sensor to transmit its data
        # Implementation depends on your SMS-based sensor protocol
        # For now, we'll assume the sensor sends data automatically via SMS
        
        # Try to read any pending SMS
        message = self.read_sms()
        if message:
            distance = self.parse_sms_distance(message)
            if distance is not None:
                from src.config import SENSOR_MAX_DISTANCE
                water_level = SENSOR_MAX_DISTANCE - distance
                timestamp = datetime.now()
                insert_water_level(timestamp, water_level, distance, "sms")
                print(f"Received SMS data: Distance={distance:.2f}m, Water Level={water_level:.2f}m")
                return True
        
        return False
    
    def send_alert(self, risk_level: str, water_level_m: float, forecast_change: float) -> bool:
        """Send SMS alerts for high risk levels"""
        if risk_level not in SMS_ALERT_RISK_LEVELS:
            return False
        
        message = SMS_ALERT_TEMPLATE.format(
            risk_level=risk_level.upper(),
            water_level=water_level_m,
            forecast_change=forecast_change
        )
        
        # Record alert in database
        alert_id = insert_alert(
            datetime.now(),
            risk_level,
            water_level_m,
            message,
            ",".join(ALERT_PHONE_NUMBERS),
            "pending"
        )
        
        # Send to all phone numbers
        success = True
        for phone_number in ALERT_PHONE_NUMBERS:
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


def trigger_sms_fallback():
    """Trigger SMS fallback to get sensor data"""
    handler = SMSHandler()
    try:
        if handler.request_sensor_data():
            print("SMS fallback: Data received successfully")
        else:
            print("SMS fallback: No data received")
    finally:
        handler.cleanup()


def send_alert_sms(risk_level: str, water_level_m: float, forecast_change: float):
    """Send SMS alert for high risk levels"""
    handler = SMSHandler()
    try:
        if handler.send_alert(risk_level, water_level_m, forecast_change):
            print(f"Alert SMS sent for {risk_level} risk level")
        else:
            print(f"Failed to send alert SMS for {risk_level}")
    finally:
        handler.cleanup()


if __name__ == "__main__":
    # Test SMS functionality
    handler = SMSHandler()
    try:
        if handler.connect():
            print("Testing SMS module...")
            # Try to read any existing messages
            message = handler.read_sms()
            if message:
                print(f"Found message: {message}")
            else:
                print("No messages found")
            
            # Test sending (uncomment to test)
            # handler.send_sms("+639123456789", "Test message from River Monitor")
    finally:
        handler.cleanup()