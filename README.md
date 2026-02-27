# LoRa WiFi System für Raspberry Pi Zero 2 W

## Komponenten

- `rolling_lora_security.py`: Rolling HMAC für sichere LoRa-Pakete
- `lora_daemon.py`: LoRa-Daemon für SX1262-HAT
- `dashboard.py`: Web-Dashboard für Node-Status
- `utils.py`: WLAN-Client-Erkennung
- `sx1262.py`: Dummy-Klasse, auf dem Pi durch Waveshare-Library ersetzen


## Installation (One-Line Setup)



### Komplettes LoRa-System (Hotspot, LoRa, Dashboard)
```bash
bash <(curl -s https://raw.githubusercontent.com/ZeroTw0016/LoRa-Test/main/lora_system/setup.sh)
```

### Nur WLAN-Access-Point mit DHCP
```bash
bash <(curl -s https://raw.githubusercontent.com/ZeroTw0016/LoRa-Test/main/lora_system/setup_ap.sh)
```

### LoRa-DHCP-Relay für WLAN-Clients
```bash
python3 lora_dhcp_relay.py
```

Das jeweilige Skript installiert und konfiguriert alles automatisch (je nach Setup).

---
Manuelle Installation (falls nötig):
1. Python 3 installieren
2. Waveshare SX1262-Library installieren (siehe https://www.waveshare.com/wiki/SX1262_868M_LoRa_HAT)
3. Flask installieren:
  ```
  pip install -r requirements.txt
  ```
4. Hostapd und dnsmasq auf dem Pi konfigurieren

## Start

- LoRa-Daemon starten:
  ```
  python lora_daemon.py <eigene_addr>
  ```
- Dashboard starten:
  ```
  python dashboard.py
  ```

## Hinweise
- Die Dummy-Klasse `sx1262.py` dient nur zur Entwicklung. Auf dem Pi muss die echte SX1262-Library verwendet werden.
- Die Datei `lora_nodes.json` wird automatisch vom Daemon gepflegt.
- WLAN-Clients werden aus `/var/lib/misc/dnsmasq.leases` gelesen.
