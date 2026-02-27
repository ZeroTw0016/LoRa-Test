import sys
import struct
import time
import threading
import json
from rolling_lora_security import RollingLoRaSecurity
from sx1262 import sx1262

NODE_STATUS_FILE = 'lora_nodes.json'

class LoRaDaemon:
    def __init__(self, lora_addr):
        self.lora_addr = lora_addr
        self.nodes = {}
        self.running = True
        self.radio = sx1262()
        self.ser = self.init_serial()

    def init_serial(self):
        # Standardwerte: /dev/ttyS0, 9600 Baud
        return serial.Serial(port=self.radio.commport, baudrate=int(self.radio.baudrate), timeout=1, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS)

    def send_status(self):
        payload = json.dumps({
            'addr': self.lora_addr,
            'timestamp': int(time.time())
        }).encode()
        packet = RollingLoRaSecurity.sign_packet(self.lora_addr, payload)
        # Sende Paket über LoRa
        try:
            self.radio.send_message(self.ser, packet.decode('latin1'))
        except Exception as e:
            print("[LoRa Send Error]", e)

    def receive_loop(self):
        while self.running:
            try:
                # Empfange Paket über LoRa
                self.radio.rcv_message(self.ser)
                # Hier müsste das empfangene Paket verarbeitet werden
                # (rcv_message gibt nur aus, du kannst es anpassen)
            except Exception as e:
                print("[LoRa Receive Error]", e)
            time.sleep(1)

    def handle_packet(self, packet):
        if len(packet) < 10:
            return
        dest_addr, timestamp = struct.unpack('>HI', packet[:6])
        payload = packet[6:]
        if RollingLoRaSecurity.authenticate_packet(dest_addr, timestamp, payload):
            try:
                data = json.loads(payload[:-4].decode())
                addr = data.get('addr')
                self.nodes[addr] = {
                    'last_seen': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'ip': None
                }
                self.save_nodes()
            except Exception:
                pass

    def save_nodes(self):
        with open(NODE_STATUS_FILE, 'w') as f:
            json.dump(self.nodes, f)

    def start(self):
        threading.Thread(target=self.receive_loop, daemon=True).start()
        while self.running:
            self.send_status()
            time.sleep(10)

if __name__ == '__main__':
    addr = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    daemon = LoRaDaemon(addr)
    daemon.start()
