#!/bin/bash
clear
# Raspberry Pi Zero 2 W: WLAN Access Point mit DHCP
set -e

sudo apt update && sudo apt upgrade -y
sudo apt install -y hostapd dnsmasq

# WLAN-Hotspot konfigurieren
if [ ! -f hostapd.conf ]; then
  echo "interface=wlan0" > hostapd.conf
  echo "driver=nl80211" >> hostapd.conf
  echo "ssid=PiAP" >> hostapd.conf
  echo "hw_mode=g" >> hostapd.conf
  echo "channel=6" >> hostapd.conf
  echo "wmm_enabled=0" >> hostapd.conf
  echo "macaddr_acl=0" >> hostapd.conf
  echo "auth_algs=1" >> hostapd.conf
  echo "ignore_broadcast_ssid=0" >> hostapd.conf
  echo "wpa=2" >> hostapd.conf
  echo "wpa_passphrase=raspberry" >> hostapd.conf
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
sudo ip addr add 192.168.50.1/24 dev wlan0 || true

echo "Access Point ist aktiv: SSID=PiAP, Passwort=raspberry"
