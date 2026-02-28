# LoRa Mesh Network & Dashboard

## Features
- Modular LoRa mesh node system (Python)
- Automatic node ID assignment
- Flask dashboard (dark mode) with device list and messaging
- Raspberry Pi WiFi Access Point for mobile dashboard access

## Quick Setup (Raspberry Pi)

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/LoRa-Test.git
cd LoRa-Test
```

### 2. Install Python Dependencies
```bash
pip install flask pyserial
```

### 3. Enable WiFi Access Point
Run the setup script as root:
```bash
sudo bash setup_wifi_ap.sh
```
- Default SSID: `LoRaMesh`
- Default Password: `loramesh123`
- Dashboard: http://192.168.50.1:5000

### 4. Run the Dashboard
```bash
python -m lora_mesh.dashboard
```

### 5. Connect Devices
- Connect your phone to the Pi WiFi.
- Use the dashboard to send/receive LoRa messages.

## Customization
- Change SSID/password in `setup_wifi_ap.sh`.
- Add more nodes by running the Python code on other Pis.

## Troubleshooting
- Ensure you run on Raspberry Pi OS (for RPi.GPIO).
- Use `sudo` for WiFi setup.
- Check serial and GPIO wiring for LoRa module.

---
For questions or improvements, open an issue or contact the maintainer.
