from .hardware import LoRaHardware
import time
import json
import os
import socket

# Packet types for mesh handshake protocol
PKT_JOIN   = 0x01  # Broadcast: I am here + my WiFi clients
PKT_ACK    = 0x02  # Unicast reply to JOIN: here are my clients
PKT_BEACON = 0x03  # Periodic broadcast: still alive + mesh snapshot
PKT_MSG    = 0x04  # User chat message

# Waveshare SX1262 868M HAT: channel = freq_MHz - 850 (for >850 MHz)
# 868 MHz -> channel 18
def _freq_to_chan(freq_mhz):
    if freq_mhz > 850:
        return max(0, min(83, int(freq_mhz) - 850))
    return max(0, min(83, int(freq_mhz) - 410))


class LoRaMeshNode:
    BROADCAST = 0xFFFF

    def __init__(self, config_path='/home/zero/LoRa-Test/node_config.json',
                 net_id=0, freq=868.0):
        self.hw          = LoRaHardware()
        self.net_id      = net_id & 0xFF
        self.chan        = _freq_to_chan(freq)
        self.config_path = config_path
        self.addr        = self._load_or_assign_addr()
        self._hostname   = socket.gethostname()
        # mesh_table: {hex_addr: {addr, rssi, hostname, wifi_clients, last_seen}}
        self.mesh_table  = {}

    def _load_or_assign_addr(self):
        if os.path.exists(self.config_path):
            with open(self.config_path) as f:
                return json.load(f).get('node_addr', 0x0001)
        addr = max(1, int(time.time()) & 0xFFFE)  # never 0x0000 or 0xFFFF
        with open(self.config_path, 'w') as f:
            json.dump({'node_addr': addr}, f)
        return addr

    def config_mesh(self):
        """
        Write configuration to the Waveshare SX1262 HAT.

        Config command format (12 bytes):
          [0xC0, 0x00, 0x09, ADDH, ADDL, NETID, REG0, REG1, CHAN, REG4, CRYPTH, CRYPTL]

        Config mode = M0=LOW(0), M1=HIGH(1)  -- from Waveshare wiki
        Normal mode = M0=LOW(0), M1=LOW(0)

        REG0 = 0x62 : 9600 baud UART, no parity, 2.4 kbps air rate
        REG1 = 0x20 : 240 B sub-packet, ambient-RSSI enabled, 22 dBm TX
        REG4 = 0xC3 : RSSI byte appended to every RX packet + fixed-point TX mode
        """
        self.hw.set_mode(0, 1)   # Config mode: M0=LOW, M1=HIGH
        time.sleep(0.1)
        self.hw.flush()
        cmd = bytes([
            0xC0,                          # permanent-save command
            0x00,                          # starting register
            0x09,                          # 9 registers to write
            (self.addr >> 8) & 0xFF,       # reg 0: ADDH
            self.addr        & 0xFF,       # reg 1: ADDL
            self.net_id,                   # reg 2: NETID
            0x62,                          # reg 3: REG0 -- 9600 baud + 2.4 kbps air
            0x20,                          # reg 4: REG1 -- 240 B, ambient-RSSI on, 22 dBm
            self.chan,                     # reg 5: CHAN  (18 for 868 MHz)
            0xC3,                          # reg 6: REG4 -- RSSI byte + fixed-point TX
            0x00,                          # reg 7: CRYPTH (no encryption)
            0x00,                          # reg 8: CRYPTL (no encryption)
        ])
        self.hw.write(cmd)
        time.sleep(0.3)
        self.hw.read()           # consume ACK echo
        self.hw.set_mode(0, 0)   # Normal mode: M0=LOW, M1=LOW
        time.sleep(0.1)

    # WiFi client discovery

    def _get_wifi_clients(self):
        """Return list of DHCP clients from dnsmasq leases."""
        clients = []
        try:
            with open('/var/lib/misc/dnsmasq.leases') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        clients.append({'ip': parts[2], 'mac': parts[1], 'name': parts[3]})
        except FileNotFoundError:
            pass
        return clients

    # Packet helpers

    def _build_payload(self, pkt_type, data):
        body = {**data, 'src': self.addr, 'host': self._hostname}
        return bytes([pkt_type]) + json.dumps(body, separators=(',', ':')).encode()

    def _send(self, target_addr, payload):
        """Prepend [ADDH, ADDL, CHAN] fixed-point header and write to UART."""
        self.hw.set_mode(0, 0)
        pkt = bytes([
            (target_addr >> 8) & 0xFF,
            target_addr        & 0xFF,
            self.chan,
            *payload,
        ])
        self.hw.write(pkt)

    # Public send API

    def send_message(self, target_addr, text):
        """Send a user chat message to target_addr (0xFFFF = broadcast)."""
        self._send(target_addr, self._build_payload(PKT_MSG, {'text': text}))

    def broadcast_join(self):
        """Announce our presence + WiFi client list to all nodes."""
        self._send(self.BROADCAST, self._build_payload(PKT_JOIN, {
            'clients': self._get_wifi_clients()
        }))

    def send_ack(self, target_addr):
        """Reply to a JOIN with our own client list."""
        self._send(target_addr, self._build_payload(PKT_ACK, {
            'clients': self._get_wifi_clients()
        }))

    def broadcast_beacon(self):
        """Periodic presence announcement with current mesh snapshot."""
        known = [{'addr': v['addr'], 'host': v['hostname']}
                 for v in self.mesh_table.values()]
        self._send(self.BROADCAST, self._build_payload(PKT_BEACON, {
            'clients': self._get_wifi_clients(),
            'mesh':    known,
        }))

    # Receive

    def recv_mesh(self):
        """
        Read one received packet.

        RX format (fixed-point mode, REG4=0xC3, RSSI byte appended):
          [SENDER_ADDH, SENDER_ADDL, SENDER_CHAN, pkt_type, json_body..., RSSI_BYTE]

        Returns (pkt_type, data_dict, rssi_dBm, sender_addr) or None.
        """
        raw = self.hw.read()
        if not raw or len(raw) < 5:
            return None

        sender_addr = (raw[0] << 8) | raw[1]
        rssi        = raw[-1] - 256          # last byte -> negative dBm
        inner       = raw[3:-1]              # strip 3-byte header + RSSI trailer

        if not inner:
            return None

        pkt_type = inner[0]
        try:
            data = json.loads(inner[1:].decode(errors='ignore'))
        except Exception:
            return None

        # Update mesh table
        src = data.get('src', sender_addr)
        self.mesh_table[hex(src)] = {
            'addr':         hex(src),
            'rssi':         rssi,
            'hostname':     data.get('host', '?'),
            'wifi_clients': data.get('clients', []),
            'last_seen':    time.strftime('%H:%M:%S'),
        }

        return pkt_type, data, rssi, src
