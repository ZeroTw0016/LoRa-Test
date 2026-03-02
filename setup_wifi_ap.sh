#!/bin/bash
# LoRa Mesh Pi WiFi AP & Dashboard Setup

# 1. Vars
SSID="ZeroLora"
PASSWORD="loramesh123"
DASH_SERVICE="lora_mesh_dashboard.service"
BACKUP_DIR="/root/lora_ap_backup"
# Zusatz: Prüfe auf WiFi 'Zero' und entscheide Verbindungsmodus
ZERO_SSID="Zero"
ZERO_PASSWORD="password" # Passwort ggf. anpassen

echo "Scanne nach WiFi-Netzwerken..."
iwlist wlan0 scan > /tmp/wifi_scan.txt
ZERO_FOUND=$(grep -i "ESSID:\"$ZERO_SSID\"" /tmp/wifi_scan.txt)

if [ -n "$ZERO_FOUND" ]; then
    echo "WiFi '$ZERO_SSID' gefunden. Verbinde..."
    backup_configs
    # wpa_supplicant config für Zero erstellen
    cat > /etc/wpa_supplicant/wpa_supplicant.conf <<EOF
network={
    ssid="$ZERO_SSID"
    psk="$ZERO_PASSWORD"
}
EOF
    # Netzwerkdienste aktivieren
    systemctl unmask wpa_supplicant.service
    systemctl unmask NetworkManager.service
    systemctl restart wpa_supplicant
    systemctl restart NetworkManager
    sleep 5
    # Prüfe Verbindung
    IWCONN=$(iw wlan0 link | grep "$ZERO_SSID")
    if [ -n "$IWCONN" ]; then
        echo "Mit '$ZERO_SSID' verbunden. Starte AP-Modus für dieses Netz."
        # Optional: Hotspot weiterleiten, falls gewünscht
        # Für Standard-AP wie bisher, einfach fortfahren
    else
        echo "Verbindung zu '$ZERO_SSID' fehlgeschlagen. Starte eigenen AP."
        rm -f /etc/wpa_supplicant/wpa_supplicant.conf
    fi
else
    echo "WiFi '$ZERO_SSID' nicht gefunden. Starte eigenen AP."
    rm -f /etc/wpa_supplicant/wpa_supplicant.conf
fi

# Helper: backup configs
backup_configs() {
    mkdir -p "$BACKUP_DIR"
    cp /etc/dhcpcd.conf "$BACKUP_DIR/dhcpcd.conf.bak"
    cp /etc/dnsmasq.conf "$BACKUP_DIR/dnsmasq.conf.bak"
    cp /etc/hostapd/hostapd.conf "$BACKUP_DIR/hostapd.conf.bak"
    [ -f /etc/wpa_supplicant/wpa_supplicant.conf ] && cp /etc/wpa_supplicant/wpa_supplicant.conf "$BACKUP_DIR/wpa_supplicant.conf.bak"
    [ -f /etc/wpa_supplicant/wpa_supplicant-wlan0.conf ] && cp /etc/wpa_supplicant/wpa_supplicant-wlan0.conf "$BACKUP_DIR/wpa_supplicant-wlan0.conf.bak"
    [ -f /boot/wpa_supplicant.conf ] && cp /boot/wpa_supplicant.conf "$BACKUP_DIR/boot_wpa_supplicant.conf.bak"
}

# Helper: restore configs
restore_configs() {
    echo "Restoring previous network configuration..."
    cp "$BACKUP_DIR/dhcpcd.conf.bak" /etc/dhcpcd.conf
    cp "$BACKUP_DIR/dnsmasq.conf.bak" /etc/dnsmasq.conf
    cp "$BACKUP_DIR/hostapd.conf.bak" /etc/hostapd/hostapd.conf
    [ -f "$BACKUP_DIR/wpa_supplicant.conf.bak" ] && cp "$BACKUP_DIR/wpa_supplicant.conf.bak" /etc/wpa_supplicant/wpa_supplicant.conf
    [ -f "$BACKUP_DIR/wpa_supplicant-wlan0.conf.bak" ] && cp "$BACKUP_DIR/wpa_supplicant-wlan0.conf.bak" /etc/wpa_supplicant/wpa_supplicant-wlan0.conf
    [ -f "$BACKUP_DIR/boot_wpa_supplicant.conf.bak" ] && cp "$BACKUP_DIR/boot_wpa_supplicant.conf.bak" /boot/wpa_supplicant.conf
}

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

# ---
# Automatische Einrichtung des lora_wifi_check.service für WiFi-Check bei jedem Gerätestart
echo "Richte lora_wifi_check.service für automatischen WiFi-Check ein..."
if [ -f "$(dirname "$0")/lora_wifi_check.service" ]; then
    cp "$(dirname "$0")/lora_wifi_check.service" /etc/systemd/system/lora_wifi_check.service
    systemctl daemon-reload
    systemctl enable lora_wifi_check.service
    echo "Service lora_wifi_check.service wurde eingerichtet und aktiviert."
else
    echo "Warnung: lora_wifi_check.service nicht gefunden. Bitte manuell kopieren."
fi

# 4. WiFi AP config (switch from managed to AP mode)
echo "Configuring WiFi AP..."
backup_configs
# Remove managed mode configs
for f in /etc/wpa_supplicant/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant-wlan0.conf /boot/wpa_supplicant.conf; do
    [ -f "$f" ] && rm "$f"
done
if [ -d /etc/NetworkManager/system-connections ]; then
    rm -f /etc/NetworkManager/system-connections/*
fi
if [ -f /etc/NetworkManager/NetworkManager.conf ]; then
    mv /etc/NetworkManager/NetworkManager.conf /etc/NetworkManager/NetworkManager.conf.bak
fi
systemctl mask wpa_supplicant.service
systemctl mask NetworkManager.service
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

# 5. Status check and fallback
sleep 5
echo "Checking AP and DHCP status..."
AP_OK=$(iw dev wlan0 info | grep -q 'type AP' && echo yes || echo no)
DNSMASQ_OK=$(systemctl is-active dnsmasq)
if [ "$AP_OK" = "yes" ] && [ "$DNSMASQ_OK" = "active" ]; then
    echo "AP and DHCP are running. Setup complete. Rebooting..."
    reboot
else
    echo "AP or DHCP failed. Restoring previous config and rebooting..."
    restore_configs
    systemctl restart dhcpcd || service dhcpcd restart || pkill -HUP dhcpcd
    systemctl restart dnsmasq
    systemctl restart hostapd
    sleep 3
    reboot
fi
