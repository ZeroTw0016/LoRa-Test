# LoRa Mesh Network & Dashboard

## Features
- Modular LoRa mesh node system (Python)
- Automatic node ID assignment
- Flask dashboard (dark mode) with device list and messaging
- Raspberry Pi WiFi Access Point for mobile dashboard access

## Quick Setup (Raspberry Pi)

### One-line install (run as root):
```bash
git clone https://github.com/ZeroTw0016/LoRa-Test.git && cd LoRa-Test && sudo bash setup_wifi_ap.sh && sudo reboot
```

### Details
1. Clones the repo and runs the setup script
2. Sets up WiFi AP (SSID: `ZeroLora`, Password: `loramesh123`)
3. Installs all dependencies and enables dashboard as a service
4. After reboot, connect your phone to `ZeroLora` and open http://192.168.50.1:5000 for chat

## Customization
- Change SSID/password in `setup_wifi_ap.sh`.
- Add more nodes by running the Python code on other Pis.

## Troubleshooting
- Ensure you run on Raspberry Pi OS (for RPi.GPIO).
- Use `sudo` for WiFi setup.
- Check serial and GPIO wiring for LoRa module.
- If you want to restore WiFi client mode, rename `/etc/wpa_supplicant/wpa_supplicant.conf.bak` back to `.conf` and reboot.

---
For questions or improvements, open an issue or contact the maintainer.
