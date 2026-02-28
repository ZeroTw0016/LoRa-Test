#!/bin/bash
# LoRa Mesh Pi WiFi AP & Dashboard Setup

# 1. Vars
SSID="ZeroLora"
PASSWORD="loramesh123"
DASH_SERVICE="lora_mesh_dashboard.service"

# 2. Installations (internet required)
echo "Updating and installing dependencies..."
apt-get update
apt-get install -y hostapd dnsmasq python3-pip
pip3 install flask pyserial --break-system-packages

# 3. Service config (dashboard)
echo "Configuring dashboard service..."
cp "$DASH_SERVICE" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$DASH_SERVICE"
systemctl start "$DASH_SERVICE"

# 4. WiFi AP config (switch from managed to AP mode)
echo "Configuring WiFi AP..."
# Remove managed mode configs
if [ -f /etc/wpa_supplicant/wpa_supplicant.conf ]; then
    rm /etc/wpa_supplicant/wpa_supplicant.conf
fi
if [ -f /etc/NetworkManager/NetworkManager.conf ]; then
    mv /etc/NetworkManager/NetworkManager.conf /etc/NetworkManager/NetworkManager.conf.bak
fi
nmcli device disconnect wlan0 2>/dev/null || true
iw dev wlan0 disconnect 2>/dev/null || true
ifconfig wlan0 down
sleep 1
ifconfig wlan0 up
# Configure static IP and dhcpcd
sed -i '/^interface wlan0$/,/^nohook wpa_supplicant$/d' /etc/dhcpcd.conf
cat <<EOC >> /etc/dhcpcd.conf
interface wlan0
static ip_address=192.168.50.1/24
nohook wpa_supplicant
EOC
systemctl restart dhcpcd || service dhcpcd restart || pkill -HUP dhcpcd
# hostapd config
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
# dnsmasq config
cat > /etc/dnsmasq.conf <<EOF
interface=wlan0
dhcp-range=192.168.50.2,192.168.50.20,255.255.255.0,24h
EOF
systemctl unmask hostapd
systemctl enable hostapd
systemctl start hostapd
systemctl start dnsmasq

# 5. Reboot
echo "Setup complete. Rebooting..."
reboot
