import socket
import threading
import time
from sx1262 import sx1262

# DHCP-Relay: Fängt DHCPDISCOVER von WLAN-Clients ab und leitet sie über LoRa weiter
WLAN_INTERFACE = 'wlan0'
DHCP_PORT = 67
BUFFER_SIZE = 1024

radio = sx1262()
ser = radio.init_serial() if hasattr(radio, 'init_serial') else None

print("LoRa DHCP-Relay gestartet.")

# UDP-Socket für DHCP auf wlan0
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.bind(("", DHCP_PORT))

# DHCP-Relay-Loop
while True:
    try:
        data, addr = sock.recvfrom(BUFFER_SIZE)
        # DHCPDISCOVER erkannt (vereinfachte Prüfung)
        if data and data[242:243] == b'\x01':  # DHCPDISCOVER (Option 53, Wert 1)
            client_mac = ':'.join(f'{b:02x}' for b in data[28:34])
            print(f"DHCPDISCOVER von {client_mac}, leite über LoRa weiter...")
            radio.send_message(ser, f"DHCPDISCOVER:{client_mac}\n")
            # Auf DHCPOFFER warten
            offer_data = None
            for _ in range(10):
                lora_data = ser.read_until()
                if lora_data:
                    msg = lora_data.decode('utf-8').strip()
                    if msg.startswith(f"DHCPOFFER:{client_mac}:"):
                        ip = msg.split(':')[2]
                        print(f"DHCPOFFER empfangen: {ip}")
                        # DHCPACK an Client senden (vereinfachte Antwort)
                        # Hier müsste ein echtes DHCPACK gebaut werden!
                        # Beispiel: sock.sendto(dhcp_ack_packet, addr)
                        offer_data = ip
                        break
                time.sleep(0.5)
            if not offer_data:
                print("Keine DHCPOFFER über LoRa erhalten.")
    except Exception as e:
        print("[DHCP-Relay Error]", e)
    time.sleep(1)
