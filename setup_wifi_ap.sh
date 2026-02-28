#!/bin/bash
# Enable Raspberry Pi WiFi AP for LoRa mesh dashboard access
# Run as root (sudo)

SSID="ZeroLora"
PASSWORD="loramesh123"

apt-get update
apt-get install -y hostapd dnsmasq python3-pip
systemctl stop hostapd
static ip_address=192.168.50.1/24
nohook wpa_supplicant" >> /etc/dhcpcd.conf
sed -i '/^interface wlan0$/,/^nohook wpa_supplicant$/d' /etc/dhcpcd.conf
echo -e "interface wlan0\nstatic ip_address=192.168.50.1/24\nnohook wpa_supplicant" >> /etc/dhcpcd.conf
service dhcpcd restart

# Remove conflicting WiFi client configs
if [ -f /etc/wpa_supplicant/wpa_supplicant.conf ]; then
	mv /etc/wpa_supplicant/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf.bak
fi
if [ -f /etc/NetworkManager/NetworkManager.conf ]; then
	mv /etc/NetworkManager/NetworkManager.conf /etc/NetworkManager/NetworkManager.conf.bak
fi

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
pip3 install flask pyserial --beak-system-packages

# Install and enable dashboard as a systemd service
cp lora_mesh_dashboard.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable lora_mesh_dashboard.service
systemctl start lora_mesh_dashboard.service

# Now the Pi is a WiFi AP at 192.168.50.1
# Connect your phone and access the dashboard chat at http://192.168.50.1:5000
