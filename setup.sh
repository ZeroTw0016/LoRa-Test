#!/bin/bash
clear
# LoRa WiFi System Setup für Raspberry Pi Zero 2 W und SX1262 LoRa HAT
set -e

sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip git hostapd dnsmasq python3-serial python3-rpi.gpio

# UART für LoRa-HAT aktivieren
sudo sed -i 's/^#*enable_uart=.*/enable_uart=1/' /boot/config.txt
sudo sed -i 's/^dtoverlay=disable-bt/dtoverlay=disable-bt/' /boot/config.txt || echo 'dtoverlay=disable-bt' | sudo tee -a /boot/config.txt

# Bluetooth-Dienst deaktivieren (Meldung unterdrücken)
sudo systemctl disable hciuart > /dev/null 2>&1 || true


# WLAN-Hotspot konfigurieren
if [ ! -f hostapd.conf ]; then
  echo "interface=wlan0" > hostapd.conf
  echo "driver=nl80211" >> hostapd.conf
  echo "ssid=LoRaHotspot" >> hostapd.conf
  echo "hw_mode=g" >> hostapd.conf
  echo "channel=6" >> hostapd.conf
  echo "wmm_enabled=0" >> hostapd.conf
  echo "macaddr_acl=0" >> hostapd.conf
  echo "auth_algs=1" >> hostapd.conf
  echo "ignore_broadcast_ssid=0" >> hostapd.conf
  echo "wpa=2" >> hostapd.conf
  echo "wpa_passphrase=LoRa2026" >> hostapd.conf
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
sudo systemctl restart hostapd
sudo systemctl restart dnsmasq

# Netzwerk konfigurieren
echo "Konfiguriere WLAN-Hotspot und statische IP..."
if [ ! -f hostapd.conf ]; then
  echo "interface=wlan0" > hostapd.conf
  echo "driver=nl80211" >> hostapd.conf
  echo "ssid=LoRaHotspot" >> hostapd.conf
  echo "hw_mode=g" >> hostapd.conf
  echo "channel=6" >> hostapd.conf
  echo "wmm_enabled=0" >> hostapd.conf
  echo "macaddr_acl=0" >> hostapd.conf
  echo "auth_algs=1" >> hostapd.conf
  echo "ignore_broadcast_ssid=0" >> hostapd.conf
  echo "wpa=2" >> hostapd.conf
  echo "wpa_passphrase=LoRa2026" >> hostapd.conf
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
sudo systemctl restart hostapd
sudo systemctl restart dnsmasq


sudo ip link set wlan0 up
echo "Starte LoRa-DHCP-Client für IP-Vergabe über LoRa..."
echo "Nutze: python3 lora_dhcp_client.py <node_id>"
sudo ip addr add 192.168.50.1/24 dev wlan0 || true

# Projekt holen (falls nicht vorhanden)
if [ ! -d "lora_system" ]; then
  git clone https://github.com/ZeroTw0016/LoRa-Test.git lora_system
fi
cd lora_system

# Python-Abhängigkeiten
pip3 install -r requirements.txt

# SX1262-HAT Python-Library (aus k3rn3Lp4n1cK/SX126X-LoRa-PI-HAT-Waveshare)
if [ ! -d "SX126X-LoRa-PI-HAT-Waveshare" ]; then
  git clone https://github.com/k3rn3Lp4n1cK/SX126X-LoRa-PI-HAT-Waveshare.git
fi


# Start-Hinweis
echo "Starte LoRa-Daemon: python3 lora_daemon.py <eigene_addr>"
echo "Starte Dashboard: python3 dashboard.py"
echo "Pi und LoRa-HAT sind jetzt komplett konfiguriert!"
echo "Um WLAN-Clients über LoRa mit IP zu versorgen, nutze: python3 lora_dhcp_relay.py"
