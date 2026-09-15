#!/usr/bin/env python3

import spidev
import lgpio
import time


# ============================================================
# RFM95 / SX1276 REGISTERS
# ============================================================

REG_FIFO                = 0x00
REG_OP_MODE             = 0x01

REG_FRF_MSB             = 0x06
REG_FRF_MID             = 0x07
REG_FRF_LSB             = 0x08

REG_PA_CONFIG            = 0x09
REG_LNA                  = 0x0C

REG_FIFO_ADDR_PTR       = 0x0D
REG_FIFO_TX_BASE_ADDR   = 0x0E
REG_FIFO_RX_BASE_ADDR   = 0x0F
REG_FIFO_RX_CURRENT     = 0x10

REG_IRQ_FLAGS            = 0x12
REG_RX_NB_BYTES         = 0x13

REG_MODEM_STAT           = 0x18
REG_PKT_SNR_VALUE       = 0x19
REG_PKT_RSSI_VALUE      = 0x1A

REG_HOP_CHANNEL          = 0x1C

REG_MODEM_CONFIG_1      = 0x1D
REG_MODEM_CONFIG_2      = 0x1E

REG_PREAMBLE_MSB        = 0x20
REG_PREAMBLE_LSB        = 0x21

REG_MODEM_CONFIG_3      = 0x26

REG_DIO_MAPPING_1       = 0x40
REG_VERSION             = 0x42


# ============================================================
# RFM95 MODES
# ============================================================

MODE_LONG_RANGE_MODE = 0x80

MODE_SLEEP            = 0x00
MODE_STDBY            = 0x01
MODE_RX_CONTINUOUS    = 0x05


# ============================================================
# IRQ FLAGS
# ============================================================

IRQ_RX_TIMEOUT         = 0x80
IRQ_RX_DONE            = 0x40
IRQ_PAYLOAD_CRC_ERROR  = 0x20
IRQ_VALID_HEADER       = 0x10


# ============================================================
# SETTINGS
# ============================================================

LORA_FREQUENCY = 915.0

SPI_BUS = 0
SPI_DEVICE = 0

SPI_SPEED = 500000

# RFM95 RESET -> Raspberry Pi GPIO4
RESET_GPIO = 4


# ============================================================
# GLOBALS
# ============================================================

spi = spidev.SpiDev()
gpio_handle = None


# ============================================================
# STATISTICS
# ============================================================

packets_received = 0
crc_errors = 0
rx_events = 0


# ============================================================
# SPI FUNCTIONS
# ============================================================

def write_register(address, value):

    spi.xfer2([
        address | 0x80,
        value & 0xFF
    ])


def read_register(address):

    result = spi.xfer2([
        address & 0x7F,
        0x00
    ])

    return result[1]


def read_fifo(length):

    result = spi.xfer2(
        [REG_FIFO] + [0x00] * length
    )

    return result[1:]


# ============================================================
# RESET
# ============================================================

def reset_rfm95():

    print("Resetting RFM95...")

    lgpio.gpio_write(
        gpio_handle,
        RESET_GPIO,
        0
    )

    time.sleep(0.1)

    lgpio.gpio_write(
        gpio_handle,
        RESET_GPIO,
        1
    )

    time.sleep(0.1)


# ============================================================
# SET FREQUENCY
# ============================================================

def set_frequency(freq_mhz):

    # SX1276:
    #
    # Fstep = 32 MHz / 2^19
    #
    # Fstep = 61.03515625 Hz

    frf = int(
        freq_mhz * 1000000 / 61.03515625
    )

    write_register(
        REG_FRF_MSB,
        (frf >> 16) & 0xFF
    )

    write_register(
        REG_FRF_MID,
        (frf >> 8) & 0xFF
    )

    write_register(
        REG_FRF_LSB,
        frf & 0xFF
    )


# ============================================================
# START CONTINUOUS RX
# ============================================================

def start_receive():

    # Clear all IRQ flags
    write_register(
        REG_IRQ_FLAGS,
        0xFF
    )

    # Set FIFO pointer to RX base
    rx_base = read_register(
        REG_FIFO_RX_BASE_ADDR
    )

    write_register(
        REG_FIFO_ADDR_PTR,
        rx_base
    )

    # Continuous RX
    write_register(
        REG_OP_MODE,
        MODE_LONG_RANGE_MODE |
        MODE_RX_CONTINUOUS
    )


# ============================================================
# CONFIGURE LORA
# ============================================================

def configure_lora():

    print("Configuring LoRa...")

    # --------------------------------------------------------
    # LoRa + SLEEP
    # --------------------------------------------------------

    write_register(
        REG_OP_MODE,
        MODE_LONG_RANGE_MODE |
        MODE_SLEEP
    )

    time.sleep(0.01)

    # --------------------------------------------------------
    # Frequency
    # --------------------------------------------------------

    set_frequency(
        LORA_FREQUENCY
    )

    # --------------------------------------------------------
    # FIFO
    # --------------------------------------------------------

    write_register(
        REG_FIFO_TX_BASE_ADDR,
        0x00
    )

    write_register(
        REG_FIFO_RX_BASE_ADDR,
        0x00
    )

    write_register(
        REG_FIFO_ADDR_PTR,
        0x00
    )

    # --------------------------------------------------------
    # MODEM CONFIG 1
    #
    # BW  = 125 kHz
    # CR  = 4/5
    # Header = Explicit
    #
    # BW125 = 7 << 4 = 0x70
    # CR4/5 = 1 << 1 = 0x02
    #
    # Result = 0x72
    # --------------------------------------------------------

    write_register(
        REG_MODEM_CONFIG_1,
        0x72
    )

    # --------------------------------------------------------
    # MODEM CONFIG 2
    #
    # SF7
    # CRC ON
    # --------------------------------------------------------

    write_register(
        REG_MODEM_CONFIG_2,
        0x74
    )

    # --------------------------------------------------------
    # MODEM CONFIG 3
    #
    # AGC automatic ON
    # Low data rate optimization OFF
    # --------------------------------------------------------

    write_register(
        REG_MODEM_CONFIG_3,
        0x04
    )

    # --------------------------------------------------------
    # PREAMBLE = 8
    # --------------------------------------------------------

    write_register(
        REG_PREAMBLE_MSB,
        0x00
    )

    write_register(
        REG_PREAMBLE_LSB,
        0x08
    )

    # --------------------------------------------------------
    # LNA
    # --------------------------------------------------------

    write_register(
        REG_LNA,
        0x23
    )

    # --------------------------------------------------------
    # DIO0 = RxDone
    # --------------------------------------------------------

    write_register(
        REG_DIO_MAPPING_1,
        0x00
    )

    # --------------------------------------------------------
    # STANDBY
    # --------------------------------------------------------

    write_register(
        REG_OP_MODE,
        MODE_LONG_RANGE_MODE |
        MODE_STDBY
    )

    time.sleep(0.01)

    # --------------------------------------------------------
    # START RX
    # --------------------------------------------------------

    start_receive()

    time.sleep(0.05)

    print()
    print("LoRa configuration:")
    print(f"  Frequency : {LORA_FREQUENCY} MHz")
    print("  Bandwidth : 125 kHz")
    print("  SF        : 7")
    print("  Coding    : 4/5")
    print("  CRC       : ON")
    print("  Header    : Explicit")
    print()


# ============================================================
# PRINT MODEM STATUS
# ============================================================

def print_modem_status():

    status = read_register(
        REG_MODEM_STAT
    )

    signal_detected = bool(
        status & 0x01
    )

    signal_synchronized = bool(
        status & 0x02
    )

    rx_ongoing = bool(
        status & 0x04
    )

    print(
        f"Modem status : 0x{status:02X} "
        f"(Detected={signal_detected}, "
        f"Sync={signal_synchronized}, "
        f"RX={rx_ongoing})"
    )


# ============================================================
# PROCESS RECEIVED PACKET
# ============================================================

def receive_packet(irq_flags):

    global packets_received
    global crc_errors
    global rx_events

    rx_events += 1

    print()
    print("==========================================")
    print(f"RxDone!  Event #{rx_events}")

    print(
        f"IRQ flags    : 0x{irq_flags:02X}"
    )

    # --------------------------------------------------------
    # Check CRC
    # --------------------------------------------------------

    if irq_flags & IRQ_PAYLOAD_CRC_ERROR:

        crc_errors += 1

        print("RESULT       : CRC ERROR")
        print(
            f"CRC errors   : {crc_errors}"
        )

        # Clear IRQ
        write_register(
            REG_IRQ_FLAGS,
            0xFF
        )

        # Re-arm RX
        start_receive()

        print("Receiver re-armed.")
        print("==========================================")

        return

    # --------------------------------------------------------
    # Valid header
    # --------------------------------------------------------

    if irq_flags & IRQ_VALID_HEADER:

        print("Header       : VALID")

    # --------------------------------------------------------
    # Packet length
    # --------------------------------------------------------

    packet_length = read_register(
        REG_RX_NB_BYTES
    )

    print(
        f"Packet length: {packet_length}"
    )

    # --------------------------------------------------------
    # FIFO current address
    # --------------------------------------------------------

    fifo_address = read_register(
        REG_FIFO_RX_CURRENT
    )

    print(
        f"FIFO address : 0x{fifo_address:02X}"
    )

    # --------------------------------------------------------
    # Set FIFO pointer
    # --------------------------------------------------------

    write_register(
        REG_FIFO_ADDR_PTR,
        fifo_address
    )

    # --------------------------------------------------------
    # Read packet
    # --------------------------------------------------------

    data = read_fifo(
        packet_length
    )

    # --------------------------------------------------------
    # Raw bytes
    # --------------------------------------------------------

    print(
        "Raw bytes    :",
        " ".join(
            f"{b:02X}" for b in data
        )
    )

    # --------------------------------------------------------
    # RadioHead packet
    #
    # RadioHead adds:
    #
    # [TO][FROM][ID][FLAGS]
    #
    # First 4 bytes are RadioHead header.
    # --------------------------------------------------------

    if len(data) >= 4:

        rh_header = data[:4]

        payload = data[4:]

        print(
            "RH header    :",
            " ".join(
                f"{b:02X}"
                for b in rh_header
            )
        )

    else:

        payload = data

        print(
            "RH header    : unavailable"
        )

    # --------------------------------------------------------
    # Decode payload
    # --------------------------------------------------------

    message = bytes(
        payload
    ).decode(
        "ascii",
        errors="replace"
    )

    print(
        f"Payload      : {message}"
    )

    # --------------------------------------------------------
    # RSSI
    # --------------------------------------------------------

    raw_rssi = read_register(
        REG_PKT_RSSI_VALUE
    )

    rssi = raw_rssi - 157

    print(
        f"RSSI         : {rssi} dBm"
    )

    # --------------------------------------------------------
    # SNR
    # --------------------------------------------------------

    raw_snr = read_register(
        REG_PKT_SNR_VALUE
    )

    if raw_snr & 0x80:

        raw_snr -= 256

    snr = raw_snr / 4.0

    print(
        f"SNR          : {snr:.2f} dB"
    )

    # --------------------------------------------------------
    # Count packet
    # --------------------------------------------------------

    packets_received += 1

    print(
        f"Packets OK   : {packets_received}"
    )

    # --------------------------------------------------------
    # Clear IRQ
    # --------------------------------------------------------

    write_register(
        REG_IRQ_FLAGS,
        0xFF
    )

    # --------------------------------------------------------
    # Re-arm receiver
    # --------------------------------------------------------

    start_receive()

    print("Receiver re-armed.")
    print("==========================================")


# ============================================================
# DIAGNOSTIC CHECK
# ============================================================

def diagnostic_check():

    global last_status_print

    now = time.time()

    # Print modem status every 2 seconds
    if now - last_status_print >= 2:

        status = read_register(
            REG_MODEM_STAT
        )

        op_mode = read_register(
            REG_OP_MODE
        )

        irq = read_register(
            REG_IRQ_FLAGS
        )

        print(
            f"[STATUS] "
            f"OP_MODE=0x{op_mode:02X} "
            f"IRQ=0x{irq:02X} "
            f"MODEM=0x{status:02X} "
            f"RX_OK={packets_received} "
            f"CRC_ERR={crc_errors}"
        )

        last_status_print = now


# ============================================================
# MAIN
# ============================================================

last_status_print = 0


def main():

    global gpio_handle
    global crc_errors

    print()
    print("==========================================")
    print(" RFM95 LoRa Diagnostic Receiver - RPi 5")
    print("==========================================")
    print()

    # --------------------------------------------------------
    # SPI
    # --------------------------------------------------------

    print("Initializing SPI...")

    spi.open(
        SPI_BUS,
        SPI_DEVICE
    )

    spi.max_speed_hz = SPI_SPEED
    spi.mode = 0

    print(
        f"SPI opened: /dev/spidev{SPI_BUS}.{SPI_DEVICE}"
    )

    # --------------------------------------------------------
    # GPIO
    # --------------------------------------------------------

    gpio_handle = lgpio.gpiochip_open(
        0
    )

    lgpio.gpio_claim_output(
        gpio_handle,
        RESET_GPIO,
        1
    )

    # --------------------------------------------------------
    # Reset
    # --------------------------------------------------------

    reset_rfm95()

    # --------------------------------------------------------
    # Check chip
    # --------------------------------------------------------

    version = read_register(
        REG_VERSION
    )

    print(
        f"RFM95 version: 0x{version:02X}"
    )

    if version != 0x12:

        print()
        print("ERROR!")
        print(
            "Expected RFM95 version 0x12"
        )

        spi.close()

        lgpio.gpiochip_close(
            gpio_handle
        )

        return

    print("RFM95 detected!")

    # --------------------------------------------------------
    # Configure
    # --------------------------------------------------------

    configure_lora()

    print("Listening for LoRa packets...")
    print()
    print("Diagnostic information will appear")
    print("every 2 seconds.")
    print()
    print("Press CTRL+C to stop.")
    print()

    # --------------------------------------------------------
    # Receive loop
    # --------------------------------------------------------

    try:

        while True:

            irq_flags = read_register(
                REG_IRQ_FLAGS
            )

            # ----------------------------------------------
            # RxDone
            # ----------------------------------------------

            if irq_flags & IRQ_RX_DONE:

                receive_packet(
                    irq_flags
                )

            # ----------------------------------------------
            # CRC error without RxDone
            # ----------------------------------------------

            elif irq_flags & IRQ_PAYLOAD_CRC_ERROR:

                print()
                print(
                    "[EVENT] CRC error"
                )

                crc_errors += 1

                write_register(
                    REG_IRQ_FLAGS,
                    0xFF
                )

                start_receive()

            # ----------------------------------------------
            # Diagnostics
            # ----------------------------------------------

            diagnostic_check()

            time.sleep(0.005)

    except KeyboardInterrupt:

        print()
        print("Stopping receiver...")

    finally:

        print()
        print("==========================================")
        print("FINAL STATISTICS")
        print("==========================================")
        print(
            f"Packets received : {packets_received}"
        )
        print(
            f"CRC errors       : {crc_errors}"
        )
        print(
            f"RxDone events    : {rx_events}"
        )
        print("==========================================")

        try:

            write_register(
                REG_OP_MODE,
                MODE_LONG_RANGE_MODE |
                MODE_SLEEP
            )

        except Exception:
            pass

        spi.close()

        if gpio_handle is not None:

            lgpio.gpiochip_close(
                gpio_handle
            )

        print("Receiver stopped.")


if __name__ == "__main__":
    main()