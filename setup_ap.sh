#!/bin/bash
clear
# Raspberry Pi Zero 2 W: WLAN Access Point, IP via LoRa-DHCP
set -e

# Zentrale WLAN-Parameter (werden vom Main übernommen)
SSID="LoRaHotspot"
WPA_PASSPHRASE="LoRa2026"

sudo apt update && sudo apt upgrade -y
sudo apt install -y hostapd bluez pi-bluetooth python3 python3-serial

# Bluetooth aktivieren
sudo rfkill unblock bluetooth || true
sudo systemctl unmask bluetooth || true
sudo systemctl enable bluetooth
sudo systemctl restart bluetooth || true
sudo systemctl enable hciuart || true
sudo systemctl restart hciuart || true

# WLAN-Hotspot konfigurieren
if [ ! -f hostapd.conf ]; then
  echo "interface=wlan0" > hostapd.conf
  echo "driver=nl80211" >> hostapd.conf
  echo "ssid=$SSID" >> hostapd.conf
  echo "hw_mode=g" >> hostapd.conf
  echo "channel=6" >> hostapd.conf
  echo "wmm_enabled=0" >> hostapd.conf
  echo "macaddr_acl=0" >> hostapd.conf
  echo "auth_algs=1" >> hostapd.conf
  echo "ignore_broadcast_ssid=0" >> hostapd.conf
  echo "wpa=2" >> hostapd.conf
  echo "wpa_passphrase=$WPA_PASSPHRASE" >> hostapd.conf
  echo "wpa_key_mgmt=WPA-PSK" >> hostapd.conf
  echo "wpa_pairwise=TKIP" >> hostapd.conf
  echo "rsn_pairwise=CCMP" >> hostapd.conf
fi
sudo cp hostapd.conf /etc/hostapd/hostapd.conf
sudo rfkill unblock wifi
sudo systemctl unmask hostapd
sudo systemctl enable hostapd
sudo systemctl stop hostapd || true
# Starte hostapd in screen, abbruchresistent
screen -dmS hostapd-restart bash -c '
  while true; do
    sudo systemctl restart hostapd
    sleep 5
    systemctl is-active --quiet hostapd || continue
    sleep 3600
  done
'
sudo systemctl disable dnsmasq >/dev/null 2>&1 || true
sudo systemctl stop dnsmasq >/dev/null 2>&1 || true

sudo ip link set wlan0 up

# Eigene AP-IP über LoRa-DHCP beziehen
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_ID="$(hostname)"

cat <<EOF | sudo tee /etc/systemd/system/lora-dhcp-client.service > /dev/null
[Unit]
Description=LoRa DHCP Client for AP IP assignment
After=network-online.target hostapd.service
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${SCRIPT_DIR}
ExecStart=/usr/bin/python3 ${SCRIPT_DIR}/lora_dhcp_client.py ${NODE_ID}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable lora-dhcp-client.service
sudo systemctl stop lora-dhcp-client.service || true
# Starte LoRa-DHCP-Client in screen, abbruchresistent
screen -dmS lora-dhcp-client bash -c '
  while true; do
    sudo systemctl restart lora-dhcp-client.service
    sleep 5
    systemctl is-active --quiet lora-dhcp-client.service || continue
    sleep 3600
  done
'

echo "Access Point ist aktiv: SSID=$SSID, Passwort=$WPA_PASSPHRASE"
echo "Die AP-IP wird per LoRa-DHCP bezogen (Service: lora-dhcp-client.service, screen: lora-dhcp-client)."
