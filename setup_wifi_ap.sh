#!/bin/bash
# Enable Raspberry Pi WiFi AP for LoRa mesh dashboard access
# Run as root (sudo)

SSID="LoRaMesh"
PASSWORD="loramesh123"

apt-get update
apt-get install -y hostapd dnsmasq python3-pip
systemctl stop hostapd
echo -e "interface wlan0
static ip_address=192.168.50.1/24
nohook wpa_supplicant" >> /etc/dhcpcd.conf
service dhcpcd restart

cat > /etc/hostapd/hostapd.conf <<EOF
interface=wlan0
driver=nl80211
ssid=$SSID
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$PASSWORD
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF

sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

cat > /etc/dnsmasq.conf <<EOF
interface=wlan0
dhcp-range=192.168.50.2,192.168.50.20,255.255.255.0,24h
EOF

systemctl start hostapd
systemctl start dnsmasq

# Install Python dependencies
pip3 install flask pyserial

# Now the Pi is a WiFi AP at 192.168.50.1
# Connect your phone and access the dashboard at http://192.168.50.1:5000
