import time
import json
from sx1262 import sx1262

# Einfache IP-Vergabe für LoRa-Nodes
IP_POOL = [f"192.168.50.{i}" for i in range(10, 100)]
LEASES = {}
LEASE_TIME = 3600  # Sekunden

radio = sx1262()
ser = radio.init_serial() if hasattr(radio, 'init_serial') else None

print("LoRa DHCP-Server gestartet.")

while True:
    # Empfange DHCP-Request über LoRa
    if ser:
        try:
            data = ser.read_until()
            if not data:
                time.sleep(1)
                continue
            msg = data.decode('utf-8').strip()
            if msg.startswith('DHCPDISCOVER:'):
                node_id = msg.split(':')[1]
                # IP zuweisen
                if node_id not in LEASES:
                    ip = IP_POOL[len(LEASES) % len(IP_POOL)]
                    LEASES[node_id] = {'ip': ip, 'expires': time.time() + LEASE_TIME}
                else:
                    ip = LEASES[node_id]['ip']
                # DHCP-OFFER senden
                offer = f"DHCPOFFER:{node_id}:{ip}"
                radio.send_message(ser, offer + '\n')
                print(f"DHCP-OFFER an {node_id}: {ip}")
        except Exception as e:
            print("[DHCP-Server Error]", e)
    time.sleep(1)
