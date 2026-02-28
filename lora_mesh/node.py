from .hardware import LoRaHardware
import time
import json
import os

class LoRaMeshNode:
    def __init__(self, config_path='node_config.json', net_id=0x1234, freq=868.125):
        self.hw = LoRaHardware()
        self.net_id = net_id
        self.freq = int((freq-410.125)*1000/0.0625)
        self.config_path = config_path
        self.addr = self.load_or_assign_id()

    def load_or_assign_id(self):
        if os.path.exists(self.config_path):
            with open(self.config_path) as f:
                cfg = json.load(f)
                return cfg.get('node_addr', 0xFFFF)
        # Broadcast join request
        self.hw.set_mode(0, 1)  # Config mode
        join_pkt = bytes([0xFE, 0xFE, 0x00, 0x00])
        self.hw.write(join_pkt)
        time.sleep(0.5)
        self.hw.set_mode(0, 0)  # Normal mode
        # Wait for assignment (simulate)
        assigned_id = int(time.time()) & 0xFFFF
        with open(self.config_path, 'w') as f:
            json.dump({'node_addr': assigned_id}, f)
        return assigned_id

    def config_mesh(self):
        self.hw.set_mode(0, 1)
        cfg = bytes([0xC0, 0x00, 0x01,
                     self.net_id>>8, self.net_id&0xFF,
                     self.freq>>8, self.freq&0xFF,
                     0x17, 0x43, 0x00, 0x00])
        self.hw.write(cfg)
        time.sleep(0.2)
        self.hw.set_mode(0, 0)

    def send_mesh(self, target_addr, payload):
        self.hw.set_mode(0, 0)
        pkt = bytes([(target_addr>>8), (target_addr&0xFF), int(self.freq%1000/0.125), *payload])
        self.hw.write(pkt)

    def recv_mesh(self):
        data = self.hw.read()
        if data:
            addr = (data[0]<<8) | data[1]
            freq = data[2]
            payload = data[4:-1]
            rssi = 256-data[-1] if len(data)>4 else 0
            return addr, payload, rssi
        return None
