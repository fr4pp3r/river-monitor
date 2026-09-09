import time, board, busio, digitalio
from adafruit_rfm9x import RFM9x

spi   = busio.SPI(board.SCK, board.MOSI, board.MISO)
cs    = digitalio.DigitalInOut(board.D4)   # GPIO4, software CS
reset = digitalio.DigitalInOut(board.D25)

rfm9x = RFM9x(spi, cs, reset, 915.0)
# rfm9x.tx_power = 20                         # match your module's +20dBm max

print("RX mode: listening for packets... (Ctrl+C to stop)")
while True:
    packet = rfm9x.receive(timeout=1.0)     # 1s poll
    if packet is not None:
        try:
            text = packet.decode("utf-8")
        except UnicodeDecodeError:
            text = repr(packet)
        print(f"[{time.strftime('%H:%M:%S')}] got {len(packet)}B "
              f"RSSI={rfm9x.last_rssi}dBm | {text}")
