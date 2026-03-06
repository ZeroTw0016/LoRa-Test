#!/bin/bash
# LoRa Mesh Pi WiFi AP & Dashboard Setup
set -e

# 1. Variablen aus lora_config.json lesen (falls vorhanden)
CONFIG="/home/zero/LoRa-Test/lora_config.json"
_cfg() { python3 -c "import json,sys; d=json.load(open('$CONFIG')); print(d.get(sys.argv[1], sys.argv[2]))" "$1" "$2" 2>/dev/null; }

if [ -f "$CONFIG" ]; then
    SSID=$(_cfg ap_ssid "ZeroLora")
    PASSWORD=$(_cfg ap_password "loramesh123")
    ZERO_SSID=$(_cfg client_ssid "Zero")
    ZERO_PASSWORD=$(_cfg client_password "password")
else
    SSID="ZeroLora"
    PASSWORD="loramesh123"
    ZERO_SSID="Zero"
    ZERO_PASSWORD="password"
fi

DASH_SERVICE="lora_mesh_dashboard.service"
BACKUP_DIR="/root/lora_ap_backup"
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# 2. Hilfsfunktionen (nur einmal definiert)
backup_configs() {
    mkdir -p "$BACKUP_DIR"
    [ -f /etc/dhcpcd.conf ]                              && cp /etc/dhcpcd.conf                              "$BACKUP_DIR/dhcpcd.conf.bak"
    [ -f /etc/dnsmasq.conf ]                             && cp /etc/dnsmasq.conf                             "$BACKUP_DIR/dnsmasq.conf.bak"
    [ -f /etc/hostapd/hostapd.conf ]                     && cp /etc/hostapd/hostapd.conf                     "$BACKUP_DIR/hostapd.conf.bak"
    [ -f /etc/wpa_supplicant/wpa_supplicant.conf ]       && cp /etc/wpa_supplicant/wpa_supplicant.conf       "$BACKUP_DIR/wpa_supplicant.conf.bak"
    [ -f /etc/wpa_supplicant/wpa_supplicant-wlan0.conf ] && cp /etc/wpa_supplicant/wpa_supplicant-wlan0.conf "$BACKUP_DIR/wpa_supplicant-wlan0.conf.bak"
    [ -f /boot/wpa_supplicant.conf ]                     && cp /boot/wpa_supplicant.conf                     "$BACKUP_DIR/boot_wpa_supplicant.conf.bak"
}

restore_configs() {
    echo "Wiederherstellung der vorherigen Netzwerkkonfiguration..."
    [ -f "$BACKUP_DIR/dhcpcd.conf.bak" ]               && cp "$BACKUP_DIR/dhcpcd.conf.bak"               /etc/dhcpcd.conf
    [ -f "$BACKUP_DIR/dnsmasq.conf.bak" ]              && cp "$BACKUP_DIR/dnsmasq.conf.bak"              /etc/dnsmasq.conf
    [ -f "$BACKUP_DIR/hostapd.conf.bak" ]              && cp "$BACKUP_DIR/hostapd.conf.bak"              /etc/hostapd/hostapd.conf
    [ -f "$BACKUP_DIR/wpa_supplicant.conf.bak" ]       && cp "$BACKUP_DIR/wpa_supplicant.conf.bak"       /etc/wpa_supplicant/wpa_supplicant.conf
    [ -f "$BACKUP_DIR/wpa_supplicant-wlan0.conf.bak" ] && cp "$BACKUP_DIR/wpa_supplicant-wlan0.conf.bak" /etc/wpa_supplicant/wpa_supplicant-wlan0.conf
    [ -f "$BACKUP_DIR/boot_wpa_supplicant.conf.bak" ]  && cp "$BACKUP_DIR/boot_wpa_supplicant.conf.bak"  /boot/wpa_supplicant.conf
}

setup_ap_mode() {
    echo "Konfiguriere eigenen WiFi-Hotspot ($SSID)..."
    backup_configs
    rfkill unblock wifi 2>/dev/null || true

    for f in /etc/wpa_supplicant/wpa_supplicant.conf \
              /etc/wpa_supplicant/wpa_supplicant-wlan0.conf \
              /boot/wpa_supplicant.conf; do
        [ -f "$f" ] && rm -f "$f"
    done
    [ -d /etc/NetworkManager/system-connections ] && rm -f /etc/NetworkManager/system-connections/*
    if [ -f /etc/NetworkManager/NetworkManager.conf ]; then
        mv /etc/NetworkManager/NetworkManager.conf /etc/NetworkManager/NetworkManager.conf.bak
    fi

    systemctl mask wpa_supplicant.service 2>/dev/null || true
    systemctl mask NetworkManager.service 2>/dev/null || true
    nmcli device disconnect wlan0 2>/dev/null || true
    iw dev wlan0 disconnect       2>/dev/null || true
    ifconfig wlan0 down
    sleep 1
    ifconfig wlan0 up

    sed -i '/^interface wlan0$/,/^nohook wpa_supplicant$/d' /etc/dhcpcd.conf
    cat >> /etc/dhcpcd.conf <<EOC
interface wlan0
static ip_address=192.168.50.1/24
nohook wpa_supplicant
EOC
    systemctl restart dhcpcd 2>/dev/null || service dhcpcd restart 2>/dev/null || pkill -HUP dhcpcd || true

    mkdir -p /etc/hostapd
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

    systemctl unmask hostapd
    systemctl enable hostapd
    systemctl restart hostapd
    systemctl restart dnsmasq
    sleep 3

    AP_OK=$(iw dev wlan0 info 2>/dev/null | grep -q 'type AP' && echo yes || echo no)
    DNSMASQ_OK=$(systemctl is-active dnsmasq 2>/dev/null || echo inactive)
    if [ "$AP_OK" = "yes" ] && [ "$DNSMASQ_OK" = "active" ]; then
        echo "Hotspot '$SSID' und DHCP laufen."
    else
        echo "WARNUNG: Hotspot oder DHCP nicht aktiv (AP=$AP_OK, dnsmasq=$DNSMASQ_OK)."
        restore_configs
    fi
}

setup_client_mode() {
    echo "Konfiguriere Client-Modus fuer '$ZERO_SSID'..."
    backup_configs
    rfkill unblock wifi 2>/dev/null || true

    systemctl stop hostapd    2>/dev/null || true
    systemctl disable hostapd 2>/dev/null || true

    sed -i '/^interface wlan0$/,/^nohook wpa_supplicant$/d' /etc/dhcpcd.conf

    systemctl unmask wpa_supplicant.service 2>/dev/null || true
    systemctl unmask NetworkManager.service 2>/dev/null || true

    cat > /etc/wpa_supplicant/wpa_supplicant.conf <<EOF
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=DE

network={
    ssid="$ZERO_SSID"
    psk="$ZERO_PASSWORD"
    key_mgmt=WPA-PSK
}
EOF

    systemctl restart wpa_supplicant 2>/dev/null || true
    systemctl restart NetworkManager 2>/dev/null || true
    systemctl restart dhcpcd         2>/dev/null || true
    sleep 8

    IWCONN=$(iw wlan0 link 2>/dev/null | grep -i "$ZERO_SSID" || true)
    if [ -n "$IWCONN" ]; then
        echo "Erfolgreich mit '$ZERO_SSID' verbunden."
        return 0
    else
        echo "Verbindung zu '$ZERO_SSID' fehlgeschlagen."
        return 1
    fi
}

# 3. Pakete installieren (einmalig)
echo "Installiere Abhaengigkeiten..."
apt-get install -y hostapd dnsmasq python3-pip
pip3 install flask pyserial --break-system-packages

# 4. Dashboard-Service
echo "Konfiguriere Dashboard-Service..."
cp "$SCRIPT_DIR/$DASH_SERVICE" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$DASH_SERVICE"
systemctl restart "$DASH_SERVICE"
sleep 2
echo "Status Dashboard-Service:"
systemctl status "$DASH_SERVICE" --no-pager || true

# 5. lora_wifi_check.sh erstellen – liest beim Boot lora_config.json
echo "Erstelle lora_wifi_check.sh..."
cat > /home/zero/LoRa-Test/lora_wifi_check.sh <<'WIFICHECK'
#!/bin/bash
# Laeuft bei jedem Boot: verbinde mit Hotspot "Zero" oder starte eigenen AP
CONFIG="/home/zero/LoRa-Test/lora_config.json"

if [ -f "$CONFIG" ]; then
    ZERO_SSID=$(python3 -c "import json; d=json.load(open('/home/zero/LoRa-Test/lora_config.json')); print(d.get('client_ssid','Zero'))" 2>/dev/null) || ZERO_SSID="Zero"
    ZERO_PASSWORD=$(python3 -c "import json; d=json.load(open('/home/zero/LoRa-Test/lora_config.json')); print(d.get('client_password','password'))" 2>/dev/null) || ZERO_PASSWORD="password"
    SSID=$(python3 -c "import json; d=json.load(open('/home/zero/LoRa-Test/lora_config.json')); print(d.get('ap_ssid','ZeroLora'))" 2>/dev/null) || SSID="ZeroLora"
    PASSWORD=$(python3 -c "import json; d=json.load(open('/home/zero/LoRa-Test/lora_config.json')); print(d.get('ap_password','loramesh123'))" 2>/dev/null) || PASSWORD="loramesh123"
else
    ZERO_SSID="Zero"
    ZERO_PASSWORD="password"
    SSID="ZeroLora"
    PASSWORD="loramesh123"
fi

rfkill unblock wifi 2>/dev/null || true
sleep 3

echo "Suche nach WiFi '$ZERO_SSID'..."
iwlist wlan0 scan 2>/dev/null > /tmp/wifi_scan.txt
ZERO_FOUND=$(grep -i "ESSID:\"$ZERO_SSID\"" /tmp/wifi_scan.txt || true)

if [ -n "$ZERO_FOUND" ]; then
    echo "'$ZERO_SSID' gefunden. Versuche Verbindung..."
    systemctl stop hostapd    2>/dev/null || true
    systemctl unmask wpa_supplicant.service 2>/dev/null || true
    systemctl unmask NetworkManager.service 2>/dev/null || true
    sed -i '/^interface wlan0$/,/^nohook wpa_supplicant$/d' /etc/dhcpcd.conf

    cat > /etc/wpa_supplicant/wpa_supplicant.conf <<EOF
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=DE

network={
    ssid="$ZERO_SSID"
    psk="$ZERO_PASSWORD"
    key_mgmt=WPA-PSK
}
EOF
    systemctl restart wpa_supplicant 2>/dev/null || true
    systemctl restart NetworkManager 2>/dev/null || true
    systemctl restart dhcpcd         2>/dev/null || true
    sleep 8

    IWCONN=$(iw wlan0 link 2>/dev/null | grep -i "$ZERO_SSID" || true)
    if [ -n "$IWCONN" ]; then
        echo "Verbunden mit '$ZERO_SSID'. Client-Modus aktiv."
        exit 0
    else
        echo "Verbindung fehlgeschlagen. Starte eigenen AP."
    fi
else
    echo "'$ZERO_SSID' nicht gefunden. Starte eigenen AP."
fi

# Fallback: eigener Hotspot
for f in /etc/wpa_supplicant/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant-wlan0.conf; do
    [ -f "$f" ] && rm -f "$f"
done
systemctl mask wpa_supplicant.service 2>/dev/null || true
systemctl mask NetworkManager.service 2>/dev/null || true
nmcli device disconnect wlan0 2>/dev/null || true
iw dev wlan0 disconnect       2>/dev/null || true
ifconfig wlan0 down; sleep 1; ifconfig wlan0 up

sed -i '/^interface wlan0$/,/^nohook wpa_supplicant$/d' /etc/dhcpcd.conf
cat >> /etc/dhcpcd.conf <<EOC
interface wlan0
static ip_address=192.168.50.1/24
nohook wpa_supplicant
EOC
systemctl restart dhcpcd 2>/dev/null || true

mkdir -p /etc/hostapd
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

systemctl unmask hostapd
systemctl enable hostapd
systemctl restart hostapd
systemctl restart dnsmasq
echo "Eigener Hotspot '$SSID' gestartet."
WIFICHECK

chmod +x /home/zero/LoRa-Test/lora_wifi_check.sh

# 6. lora_wifi_check.service installieren
if [ -f "$SCRIPT_DIR/lora_wifi_check.service" ]; then
    cp "$SCRIPT_DIR/lora_wifi_check.service" /etc/systemd/system/lora_wifi_check.service
    systemctl daemon-reload
    systemctl enable lora_wifi_check.service
    echo "lora_wifi_check.service aktiviert."
else
    echo "Warnung: lora_wifi_check.service nicht gefunden."
fi

# 7. Erstes WiFi-Setup entscheiden
echo "Scanne nach WiFi-Netzwerken..."
iwlist wlan0 scan > /tmp/wifi_scan.txt 2>/dev/null || true
ZERO_FOUND=$(grep -i "ESSID:\"$ZERO_SSID\"" /tmp/wifi_scan.txt || true)

if [ -n "$ZERO_FOUND" ]; then
    if setup_client_mode; then
        echo "Client-Modus aktiv. Reboot..."
        reboot
    else
        echo "Client-Modus fehlgeschlagen. Starte eigenen AP..."
        setup_ap_mode
        reboot
    fi
else
    echo "'$ZERO_SSID' nicht in Reichweite. Starte eigenen AP..."
    setup_ap_mode
    reboot
fi