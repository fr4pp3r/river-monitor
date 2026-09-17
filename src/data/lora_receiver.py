"""
LoRa Receiver for River Monitor System
Handles RFM95W module communication using spidev + lgpio (manual SPI)
"""

import time
import struct
import threading
import spidev
import lgpio
from datetime import datetime
from typing import Optional, Callable

from src.config import (
    LORA_ENABLED, LORA_FREQUENCY, LORA_SPREADING_FACTOR, LORA_BANDWIDTH,
    LORA_CODING_RATE, LORA_RESET_PIN,
    SENSOR_MAX_DISTANCE, RAIN_BUCKET_TIP_MM,
    LORA_FALLBACK_TIMEOUT
)
from src.data.database import insert_water_level


# ============================================================
# RFM95 / SX1276 REGISTERS
# ============================================================

REG_FIFO = 0x00
REG_OP_MODE = 0x01
REG_FRF_MSB = 0x06
REG_FRF_MID = 0x07
REG_FRF_LSB = 0x08
REG_PA_CONFIG = 0x09
REG_LNA = 0x0C
REG_FIFO_ADDR_PTR = 0x0D
REG_FIFO_TX_BASE_ADDR = 0x0E
REG_FIFO_RX_BASE_ADDR = 0x0F
REG_FIFO_RX_CURRENT = 0x10
REG_IRQ_FLAGS = 0x12
REG_RX_NB_BYTES = 0x13
REG_MODEM_STAT = 0x18
REG_PKT_SNR_VALUE = 0x19
REG_PKT_RSSI_VALUE = 0x1A
REG_MODEM_CONFIG_1 = 0x1D
REG_MODEM_CONFIG_2 = 0x1E
REG_PREAMBLE_MSB = 0x20
REG_PREAMBLE_LSB = 0x21
REG_MODEM_CONFIG_3 = 0x26
REG_DIO_MAPPING_1 = 0x40
REG_SYNC_WORD = 0x39
REG_VERSION = 0x42
REG_PA_DAC = 0x4D

# Op modes
MODE_SLEEP = 0x00
MODE_STDBY = 0x01
MODE_TX = 0x03
MODE_RX_CONTINUOUS = 0x05
MODE_RX_SINGLE = 0x06
LONG_RANGE_MODE = 0x80

# IRQ flags
IRQ_RX_TIMEOUT = 0x80
IRQ_RX_DONE = 0x40
IRQ_PAYLOAD_CRC_ERROR = 0x20
IRQ_VALID_HEADER = 0x10

# SPI
SPI_BUS = 0
SPI_DEVICE = 0
SPI_SPEED = 100000  # 100kHz - RFM95 needs slow clock


class LoRaReceiver:
    """RFM95W LoRa module receiver using spidev + lgpio"""

    def __init__(self):
        self.spi = None
        self.gpio_handle = None
        self.last_receive_time = None

        if not LORA_ENABLED:
            print("LoRa module is DISABLED in config (LORA_ENABLED=False)")
            self.enabled = False
            return

        self.enabled = True
        self.setup_hardware()

    def setup_hardware(self):
        """Initialize SPI and GPIO using spidev + lgpio (kernel manages CS)"""
        try:
            # Open SPI device - kernel manages CS on GPIO 8 (CE0) automatically
            self.spi = spidev.SpiDev()
            self.spi.open(SPI_BUS, SPI_DEVICE)
            self.spi.max_speed_hz = SPI_SPEED
            self.spi.mode = 0

            # Open GPIO chip and claim only RST pin (kernel manages CS)
            self.gpio_handle = lgpio.gpiochip_open(0)
            lgpio.gpio_claim_output(self.gpio_handle, LORA_RESET_PIN, 1)

            # Reset module
            self.reset()

            # Check version
            version = self._read_reg(REG_VERSION)
            if version != 0x12:
                raise RuntimeError(f"RFM95 version check failed: got 0x{version:02x}, expected 0x12")

            # Configure LoRa registers
            self.configure_lora()

            print(f"LoRa receiver initialized successfully: {LORA_FREQUENCY}MHz, "
                  f"SF{LORA_SPREADING_FACTOR}, BW{LORA_BANDWIDTH}kHz, CR4/{LORA_CODING_RATE}")

        except Exception as e:
            print(f"Error initializing LoRa hardware: {e}")
            self.cleanup()
            raise

    def reset(self):
        """Reset the LoRa module"""
        lgpio.gpio_write(self.gpio_handle, LORA_RESET_PIN, 0)
        time.sleep(0.1)
        lgpio.gpio_write(self.gpio_handle, LORA_RESET_PIN, 1)
        time.sleep(0.1)

    def _write_reg(self, address: int, value: int):
        """Write to a register (address | 0x80 for write)"""
        self.spi.xfer2([address | 0x80, value & 0xFF])

    def _read_reg(self, address: int) -> int:
        """Read a register (address & 0x7F for read)"""
        resp = self.spi.xfer2([address & 0x7F, 0x00])
        return resp[1]

    def _read_fifo(self, length: int) -> list:
        """Read multiple bytes from FIFO"""
        resp = self.spi.xfer2([REG_FIFO] + [0x00] * length)
        return resp[1:]

    def _set_frequency(self, freq_mhz: float):
        """Set frequency in MHz"""
        frf = int((freq_mhz * 1000000) / 61.03515625)
        self._write_reg(REG_FRF_MSB, (frf >> 16) & 0xFF)
        self._write_reg(REG_FRF_MID, (frf >> 8) & 0xFF)
        self._write_reg(REG_FRF_LSB, frf & 0xFF)

    def configure_lora(self):
        """Configure LoRa module settings - matches working test_lora.py"""
        # LoRa + SLEEP
        self._write_reg(REG_OP_MODE, MODE_SLEEP | LONG_RANGE_MODE)
        time.sleep(0.01)

        # Frequency
        self._set_frequency(LORA_FREQUENCY)

        # FIFO
        self._write_reg(REG_FIFO_TX_BASE_ADDR, 0x00)
        self._write_reg(REG_FIFO_RX_BASE_ADDR, 0x00)
        self._write_reg(REG_FIFO_ADDR_PTR, 0x00)

        # MODEM CONFIG 1: BW=125kHz, CR=4/5, Explicit header
        # BW125 = 7 << 4 = 0x70, CR4/5 = 1 << 1 = 0x02 -> 0x72
        self._write_reg(REG_MODEM_CONFIG_1, 0x72)

        # MODEM CONFIG 2: SF7, CRC ON
        # SF7 = 7 << 4 = 0x70, CRC ON = 0x04 -> 0x74
        self._write_reg(REG_MODEM_CONFIG_2, 0x74)

        # MODEM CONFIG 3: AGC auto ON
        self._write_reg(REG_MODEM_CONFIG_3, 0x04)

        # PREAMBLE = 8
        self._write_reg(REG_PREAMBLE_MSB, 0x00)
        self._write_reg(REG_PREAMBLE_LSB, 0x08)

        # LNA boost
        self._write_reg(REG_LNA, 0x23)

        # Sync word (0x39) - MUST match RadioHead's default 0x12 (LoRa public)
        self._write_reg(REG_SYNC_WORD, 0x12)

        # DIO0 = RxDone
        self._write_reg(REG_DIO_MAPPING_1, 0x00)

        # STANDBY
        self._write_reg(REG_OP_MODE, MODE_STDBY | LONG_RANGE_MODE)
        time.sleep(0.01)

        # START CONTINUOUS RX
        self.start_receive()
        time.sleep(0.05)

        print(f"LoRa receiver initialized successfully: {LORA_FREQUENCY}MHz, "
              f"SF{LORA_SPREADING_FACTOR}, BW{LORA_BANDWIDTH}kHz, CR4/{LORA_CODING_RATE}")

    def start_receive(self):
        """Put radio in continuous receive mode"""
        # Clear all IRQ flags
        self._write_reg(REG_IRQ_FLAGS, 0xFF)

        # Set FIFO pointer to RX base
        rx_base = self._read_reg(REG_FIFO_RX_BASE_ADDR)
        self._write_reg(REG_FIFO_ADDR_PTR, rx_base)

        # Continuous RX
        self._write_reg(REG_OP_MODE, MODE_RX_CONTINUOUS | LONG_RANGE_MODE)

    def receive_packet(self, timeout: float = 1.0) -> Optional[str]:
        """Receive a LoRa packet with timeout - handles RadioHead header"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            irq_flags = self._read_reg(REG_IRQ_FLAGS)

            if irq_flags & IRQ_RX_DONE:
                # Clear IRQ flags
                self._write_reg(REG_IRQ_FLAGS, 0xFF)

                # Check CRC
                if irq_flags & IRQ_PAYLOAD_CRC_ERROR:
                    print("CRC ERROR on received packet")
                    self.start_receive()
                    return None

                # Check valid header
                if not (irq_flags & IRQ_VALID_HEADER):
                    print("Invalid header on received packet")
                    self.start_receive()
                    return None

                # Packet length
                packet_length = self._read_reg(REG_RX_NB_BYTES)
                if packet_length == 0:
                    self.start_receive()
                    return None

                # FIFO current address
                fifo_address = self._read_reg(REG_FIFO_RX_CURRENT)
                self._write_reg(REG_FIFO_ADDR_PTR, fifo_address)

                # Read packet
                data = self._read_fifo(packet_length)

                # Re-arm receiver
                self.start_receive()

                # Handle RadioHead header (first 4 bytes: TO, FROM, ID, FLAGS)
                if len(data) >= 4:
                    payload = data[4:]
                else:
                    payload = data

                # Convert to string
                try:
                    packet_str = bytes(payload).decode('ascii', errors='replace').strip()
                    return packet_str
                except UnicodeDecodeError:
                    return None

            time.sleep(0.005)  # 5ms polling - matches working test

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

    def has_stale_data(self) -> bool:
        if self.last_receive_time is None:
            return True

        time_since_last = (datetime.now() - self.last_receive_time).total_seconds()
        return time_since_last > LORA_FALLBACK_TIMEOUT

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

                if self.has_stale_data():
                    print("No LoRa data received - sensor may be offline or out of range")
                    self.last_receive_time = datetime.now()  # Reset timer

        except KeyboardInterrupt:
            print("LoRa receiver stopped")
        except Exception as e:
            print(f"LoRa receiver error: {e}")
            raise
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up SPI and GPIO"""
        if self.spi:
            self.spi.close()
        if self.gpio_handle is not None:
            lgpio.gpiochip_close(self.gpio_handle)


def start_lora_receiver():
    """Start the LoRa receiver as standalone process"""
    if not LORA_ENABLED:
        print("LoRa module is DISABLED in config. Skipping.")
        return
    receiver = LoRaReceiver()
    receiver.run()


def start_lora_receiver_async():
    """Start the LoRa receiver loop in background daemon thread.

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