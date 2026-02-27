#!/bin/bash
clear
# LoRa WiFi System Setup für Raspberry Pi Zero 2 W und SX1262 LoRa HAT
set -e

# Zentrale WLAN-Parameter (auch für APs)
SSID="LoRaHotspot"
WPA_PASSPHRASE="LoRa2026"

sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip git hostapd dnsmasq python3-serial python3-rpi.gpio bluez pi-bluetooth

# UART für LoRa-HAT aktivieren
sudo sed -i 's/^#*enable_uart=.*/enable_uart=1/' /boot/config.txt
sudo sed -i '/^dtoverlay=disable-bt$/d' /boot/config.txt

# Bluetooth aktivieren
sudo rfkill unblock bluetooth || true
sudo systemctl unmask bluetooth || true
sudo systemctl enable bluetooth
sudo systemctl restart bluetooth || true
sudo systemctl enable hciuart || true
sudo systemctl restart hciuart || true

# Projekt holen (falls nicht vorhanden)
if [ ! -d "lora_system" ]; then
  git clone https://github.com/ZeroTw0016/LoRa-Test.git lora_system
fi
cd lora_system

# Python-Abhängigkeiten (benötigt Internet)
pip3 install -r requirements.txt

# SX1262-HAT Python-Library (benötigt Internet)
if [ ! -d "SX126X-LoRa-PI-HAT-Waveshare" ]; then
  git clone https://github.com/k3rn3Lp4n1cK/SX126X-LoRa-PI-HAT-Waveshare.git
fi


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
if [ ! -f dnsmasq.conf ]; then
  echo "interface=wlan0" > dnsmasq.conf
  echo "dhcp-range=192.168.50.10,192.168.50.100,255.255.255.0,24h" >> dnsmasq.conf
fi
sudo cp hostapd.conf /etc/hostapd/hostapd.conf
sudo cp dnsmasq.conf /etc/dnsmasq.conf
sudo rfkill unblock wifi
sudo systemctl unmask hostapd
sudo systemctl enable hostapd
sudo systemctl enable dnsmasq
sudo systemctl stop hostapd || true
sudo systemctl stop dnsmasq || true
# Starte hostapd und dnsmasq in screen, abbruchresistent
screen -dmS hostapd-restart bash -c '
  while true; do
    sudo systemctl restart hostapd
    sleep 5
    systemctl is-active --quiet hostapd || continue
    sleep 3600
  done
'
screen -dmS dnsmasq-restart bash -c '
  while true; do
    sudo systemctl restart dnsmasq
    sleep 5
    systemctl is-active --quiet dnsmasq || continue
    sleep 3600
  done
'


sudo ip link set wlan0 up
sudo ip -4 addr flush dev wlan0
sudo ip addr add 192.168.50.1/24 dev wlan0

# Main-Node nutzt feste IP, kein LoRa-DHCP-Client
sudo systemctl disable lora-dhcp-client.service >/dev/null 2>&1 || true
sudo systemctl stop lora-dhcp-client.service >/dev/null 2>&1 || true


# Start-Hinweis
echo "Starte LoRa-Daemon: python3 lora_daemon.py <eigene_addr>"
echo "Starte Dashboard: python3 dashboard.py"
echo "Pi und LoRa-HAT sind jetzt komplett konfiguriert!"
echo "Um WLAN-Clients über LoRa mit IP zu versorgen, nutze: python3 lora_dhcp_relay.py"
echo "Main-Node IP auf wlan0 ist fest: 192.168.50.1/24"
