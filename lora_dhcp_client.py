import sys
import time
from sx1262 import sx1262
import os

radio = sx1262()
ser = radio.init_serial() if hasattr(radio, 'init_serial') else None

NODE_ID = sys.argv[1] if len(sys.argv) > 1 else 'node1'

print(f"LoRa DHCP-Client gestartet (Node-ID: {NODE_ID})")

# DHCPDISCOVER senden
if ser:
    radio.send_message(ser, f"DHCPDISCOVER:{NODE_ID}\n")

# Auf DHCPOFFER warten
while True:
    if ser:
        try:
            data = ser.read_until()
            if not data:
                time.sleep(1)
                continue
            msg = data.decode('utf-8').strip()
            if msg.startswith(f"DHCPOFFER:{NODE_ID}:"):
                ip = msg.split(':')[2]
                print(f"DHCP-OFFER empfangen: {ip}")
                # IP zuweisen
                os.system(f"sudo ip addr add {ip}/24 dev wlan0")
                print(f"IP {ip} auf wlan0 gesetzt.")
                break
        except Exception as e:
            print("[DHCP-Client Error]", e)
    time.sleep(1)
