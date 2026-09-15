"""
LoRa Receiver for River Monitor System
Handles RFM95W module communication for receiving water level sensor data
"""

import time
import struct
import threading
import spidev
from src.data.gpio_libgpiod import OutputPin, InputPin
from datetime import datetime
from typing import Optional, Callable

from src.config import (
    LORA_ENABLED, LORA_SPI_PORT, LORA_CE_PIN, LORA_CS_PIN, LORA_RESET_PIN,
    LORA_FREQUENCY, LORA_BANDWIDTH, LORA_SPREADING_FACTOR, LORA_CODING_RATE,
    SENSOR_MAX_DISTANCE, SENSOR_MAX_DISTANCE_MM, RAIN_BUCKET_TIP_MM, WATER_LEVEL_INTERVAL,
    SMS_ENABLED
)
from src.data.database import insert_water_level, get_latest_water_level
from src.data.sms_handler import trigger_sms_fallback


class LoRaReceiver:
    """RFM95W LoRa module receiver"""
    
    def __init__(self):
        self.spi = None
        self.ce_pin = None
        self.cs_pin = None
        self.rst_pin = None
        self.last_receive_time = None
        
        if not LORA_ENABLED:
            print("LoRa module is DISABLED in config (LORA_ENABLED=False)")
            self.enabled = False
            return
        
        self.enabled = True
        self.setup_hardware()

    def setup_hardware(self):
        """Initialize SPI and GPIO via libgpiod (C library)"""
        try:
            # LoRa control pins (libgpiod uses BCM numbering by default)
            self.cs_pin = OutputPin(LORA_CS_PIN, initial=True)
            self.rst_pin = OutputPin(LORA_RESET_PIN, initial=False)
            self.ce_pin = InputPin(LORA_CE_PIN)

            # Setup SPI
            self.spi = spidev.SpiDev()
            self.spi.open(0, LORA_CS_PIN)
            self.spi.max_speed_hz = 10000000
            self.spi.mode = 0b00
            
            self.gpio_setup_done = True
            
            # Reset LoRa module
            self.reset()
            
            # Configure LoRa settings
            self.configure_lora()
            
            print("LoRa receiver initialized successfully")
            
        except Exception as e:
            print(f"Error initializing LoRa hardware: {e}")
            self.cleanup()
            raise
    
    def reset(self):
        """Reset the LoRa module"""
        self.rst_pin.off()
        time.sleep(0.1)
        self.rst_pin.on()
        time.sleep(0.1)
    
    def configure_lora(self):
        """Configure LoRa module settings"""
        # Set frequency (915 MHz)
        self._write_register(0x06, self._calculate_frequency(LORA_FREQUENCY))
        
        # Set spreading factor + enable CRC (bit 2 = RxPayloadCrcOn, mandatory:
        # the sensor node's RadioHead RH_RF95 transmits with CRC enabled by
        # default, and a CRC-disabled receiver discards those packets)
        self._write_register(0x1E, (LORA_SPREADING_FACTOR << 4) | 0x04)

        # Set bandwidth (RegModemConfig1, upper nibble)
        bw = {125: 0x00, 250: 0x01, 500: 0x02}[LORA_BANDWIDTH]
        self._write_register(0x1D, bw << 4)

        # Set coding rate (RegModemConfig1, lower nibble)
        self._write_register(0x1D, self._read_register(0x1D) | (LORA_CODING_RATE << 1))
        
        # Set preamble length
        self._write_register(0x20, 0x08)  # 8 bytes preamble
        
        # Set payload length
        self._write_register(0x22, 0x40)  # Max payload length
        
        # Set low noise amplifier gain
        self._write_register(0x0C, 0x23)
        
        # Set mode to LoRa
        self._write_register(0x01, 0x80)  # Sleep mode
        time.sleep(0.01)
        self._write_register(0x01, 0x88)  # LoRa mode
        
        # Set to receive mode
        self._write_register(0x01, 0x8D)  # Continuous receive mode
        self._write_register(0x40, 0x00)  # DIO0 mapping
        
        print(f"LoRa configured: {LORA_FREQUENCY}MHz, SF{LORA_SPREADING_FACTOR}, BW{LORA_BANDWIDTH}kHz, CR4/{LORA_CODING_RATE}")
    
    def _read_register(self, address: int) -> int:
        """Read a register value"""
        self.cs_pin.off()
        self.spi.xfer2([address & 0x7F, 0x00])
        value = self.spi.xfer2([0x00])[0]
        self.cs_pin.on()
        return value

    def _write_register(self, address: int, value: int):
        """Write to a register"""
        self.cs_pin.off()
        self.spi.xfer2([address | 0x80, value])
        self.cs_pin.on()
    
    def _calculate_frequency(self, freq_mhz: float) -> int:
        """Calculate frequency register value"""
        return int((freq_mhz * 1000000) / 61.03515625)
    
    def receive_packet(self, timeout: float = 1.0) -> Optional[str]:
        """Receive a LoRa packet with timeout"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check if packet received (DIO0 goes high)
            if self.ce_pin.is_active:  # Using CE as DIO0
                # Read packet
                packet = self._read_packet()
                if packet:
                    return packet

            time.sleep(0.01)
        
        return None
    
    def _read_packet(self) -> Optional[str]:
        """Read received packet from FIFO"""
        # Check if packet is available
        irq_flags = self._read_register(0x12)
        if not (irq_flags & 0x40):  # RxDone flag
            return None
        
        # Clear IRQ flags
        self._write_register(0x12, 0x40)
        
        # Read packet length
        packet_length = self._read_register(0x13)
        
        # Read packet from FIFO
        GPIO.output(LORA_CS_PIN, GPIO.LOW)
        self.spi.xfer2([0x00])  # Read from FIFO
        packet_bytes = self.spi.xfer2([0x00] * packet_length)
        GPIO.output(LORA_CS_PIN, GPIO.HIGH)
        
        # Clear FIFO
        self._write_register(0x0D, 0x04)  # Clear FIFO
        
        # Convert to string
        try:
            packet_str = bytes(packet_bytes).decode('ascii')
            return packet_str.strip()
        except UnicodeDecodeError:
            return None
    
    def parse_packet_data(self, packet: str) -> Optional[tuple]:
        """
        Parse distance and rain tips from LoRa packet
        Expected format: "Distance=%dmm,Tips=%lu" (e.g., "Distance=1234mm,Tips=5")
        Returns: (distance_mm, rain_tips) or None
        """
        try:
            distance_mm = None
            rain_tips = 0
            
            # Parse distance - format: "Distance=%dmm"
            if "Distance=" in packet:
                dist_part = packet.split("Distance=")[1]
                if "mm" in dist_part:
                    dist_str = dist_part.split("mm")[0]
                else:
                    dist_str = dist_part
                distance_mm = int(float(dist_str))
            
            # Parse rain tips - format: "Tips=%lu"
            if "Tips=" in packet:
                tips_part = packet.split("Tips=")[1]
                rain_tips = int(float(tips_part))
            
            if distance_mm is not None:
                return distance_mm, rain_tips
            else:
                print(f"Invalid packet format: {packet}")
                return None
                
        except (ValueError, IndexError, AttributeError) as e:
            print(f"Error parsing packet '{packet}': {e}")
            return None
    
    def process_packet(self, packet: str) -> bool:
        """Process received packet and store in database"""
        parsed_data = self.parse_packet_data(packet)
        if parsed_data is None:
            print(f"Failed to parse packet: {packet}")
            return False
        
        distance_mm, rain_tips = parsed_data
        
        # Convert distance from mm to meters
        distance_m = distance_mm / 1000.0
        
        # Calculate water level (invert distance)
        water_level = SENSOR_MAX_DISTANCE - distance_m
        
        # Calculate rainfall from tips
        rainfall_mm = rain_tips * RAIN_BUCKET_TIP_MM
        
        # Store in database
        timestamp = datetime.now()
        insert_water_level(
            timestamp=timestamp,
            water_level_m=water_level,
            raw_distance_m=distance_m,
            raw_distance_mm=distance_mm,
            rain_tips=rain_tips,
            rainfall_mm=rainfall_mm,
            source="lora"
        )
        
        self.last_receive_time = timestamp
        print(f"Received LoRa data: Distance={distance_mm}mm ({distance_m:.3f}m), "
              f"Water Level={water_level:.3f}m, Rain Tips={rain_tips}, Rainfall={rainfall_mm:.1f}mm")
        
        return True
    
    def check_fallback_needed(self) -> bool:
        """Check if SMS fallback should be triggered"""
        if self.last_receive_time is None:
            return True
        
        time_since_last = (datetime.now() - self.last_receive_time).total_seconds()
        return time_since_last > WATER_LEVEL_INTERVAL * 5  # 5 missed intervals
    
    def run(self, callback: Optional[Callable] = None):
        """Main receive loop"""
        if not self.enabled:
            print("LoRa receiver is disabled, skipping run loop")
            return
        
        print("Starting LoRa receiver...")
        
        try:
            while True:
                packet = self.receive_packet(timeout=1.0)
                if packet:
                    if self.process_packet(packet):
                        if callback:
                            callback()
                
                # Check if fallback needed
                if self.check_fallback_needed():
                    if SMS_ENABLED:
                        print("No LoRa data received, triggering SMS fallback...")
                        trigger_sms_fallback()
                    else:
                        print("No LoRa data received, SMS fallback is DISABLED")
                    self.last_receive_time = datetime.now()  # Reset timer
                
        except KeyboardInterrupt:
            print("LoRa receiver stopped")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up GPIO and SPI"""
        if self.spi:
            self.spi.close()
        # gpiozero devices clean up automatically on __del__,
        # but we explicitly close them for deterministic release
        if self.cs_pin:
            self.cs_pin.close()
        if self.rst_pin:
            self.rst_pin.close()
        if self.ce_pin:
            self.ce_pin.close()


def start_lora_receiver():
    """Start the LoRa receiver as a standalone process"""
    if not LORA_ENABLED:
        print("LoRa module is DISABLED in config. Skipping.")
        return
    receiver = LoRaReceiver()
    receiver.run()


def start_lora_receiver_async():
    """Start the LoRa receiver loop in a background daemon thread.

    Returns the created thread so callers can inspect/join it if needed.
    The thread is a daemon, so it dies automatically when the process exits.
    """
    if not LORA_ENABLED:
        print("LoRa module is DISABLED in config. Skipping.")
        return None

    def _run():
        try:
            receiver = LoRaReceiver()
            receiver.run()
        except Exception as e:
            # GPIO/SPI permission errors, missing hardware, etc. must not
            # crash the web dashboard - log and keep serving.
            print(f"LoRa receiver thread failed: {e}")

    thread = threading.Thread(target=_run, name="lora-receiver", daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    start_lora_receiver()
