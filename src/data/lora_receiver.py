"""
LoRa Receiver for River Monitor System
Handles RFM95W module communication using adafruit-circuitpython-rfm9x
"""

import time
import threading
import busio
import digitalio
import board
from datetime import datetime
from typing import Optional, Callable

try:
    import adafruit_rfm9x
except ImportError:
    adafruit_rfm9x = None

from src.config import (
    LORA_ENABLED, LORA_FREQUENCY, LORA_SPREADING_FACTOR, LORA_BANDWIDTH,
    LORA_CODING_RATE, LORA_CS_PIN, LORA_RESET_PIN, LORA_CE_PIN,
    SENSOR_MAX_DISTANCE, RAIN_BUCKET_TIP_MM, WATER_LEVEL_INTERVAL,
    SMS_ENABLED
)
from src.data.database import insert_water_level, get_latest_water_level
from src.data.sms_handler import trigger_sms_fallback


class LoRaReceiver:
    """RFM95W LoRa module receiver using adafruit-circuitpython-rfm9x"""

    def __init__(self):
        self.rfm9x = None
        self.last_receive_time = None

        if not LORA_ENABLED:
            print("LoRa module is DISABLED in config (LORA_ENABLED=False)")
            self.enabled = False
            return

        if adafruit_rfm9x is None:
            print("ERROR: adafruit-circuitpython-rfm9x not installed")
            self.enabled = False
            return

        self.enabled = True
        self.setup_hardware()

    def setup_hardware(self):
        """Initialize SPI and RFM95 via adafruit blinka"""
        try:
            # SPI bus - RFM95 needs slow SPI clock (100kHz) to respond reliably
            spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
            # Set SPI baudrate to 100kHz (RFM95 needs slow clock to respond)
            spi.try_lock()
            spi.configure(baudrate=100000)
            spi.unlock()

            # Chip select and reset pins (BCM numbering via blinka)
            cs = digitalio.DigitalInOut(getattr(board, f"D{LORA_CS_PIN}"))
            reset = digitalio.DigitalInOut(getattr(board, f"D{LORA_RESET_PIN}"))

            # Initialize RFM95
            self.rfm9x = adafruit_rfm9x.RFM9x(
                spi, cs, reset, LORA_FREQUENCY
            )

            # Configure LoRa settings
            self.rfm9x.spreading_factor = LORA_SPREADING_FACTOR
            self.rfm9x.signal_bandwidth = LORA_BANDWIDTH
            self.rfm9x.coding_rate = LORA_CODING_RATE
            self.rfm9x.preamble_length = 8
            self.rfm9x.enable_crc = True  # Match RadioHead's CRC-on default

            print(f"LoRa receiver initialized successfully: {LORA_FREQUENCY}MHz, "
                  f"SF{LORA_SPREADING_FACTOR}, BW{LORA_BANDWIDTH}kHz, CR4/{LORA_CODING_RATE}")

        except Exception as e:
            print(f"Error initializing LoRa hardware: {e}")
            raise

    def receive_packet(self, timeout: float = 1.0) -> Optional[str]:
        """Receive a LoRa packet with timeout"""
        if not self.rfm9x:
            return None

        start_time = time.time()
        while time.time() - start_time < timeout:
            packet = self.rfm9x.receive(timeout=0.1)
            if packet:
                try:
                    return packet.decode('ascii').strip()
                except UnicodeDecodeError:
                    return None
            time.sleep(0.01)
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

            if "Distance=" in packet:
                dist_part = packet.split("Distance=")[1]
                if "mm" in dist_part:
                    dist_str = dist_part.split("mm")[0]
                else:
                    dist_str = dist_part
                distance_mm = int(float(dist_str))

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
        except Exception as e:
            print(f"LoRa receiver error: {e}")
            raise

    def cleanup(self):
        """Clean up"""
        if self.rfm9x:
            self.rfm9x.sleep()


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
            print(f"LoRa receiver thread failed: {e}")

    thread = threading.Thread(target=_run, name="lora-receiver", daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    start_lora_receiver()