from flask import Flask, render_template, request, jsonify
import threading
import subprocess
import time
import json
import os

from .node import LoRaMeshNode

app = Flask(__name__)
node = LoRaMeshNode()
node.config_mesh()

# Store seen devices and message history in memory
connected_devices = {}
message_history = []

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lora_config.json')
CONFIG_DEFAULTS = {
    'ap_ssid': 'ZeroLora',
    'ap_password': 'loramesh123',
    'client_ssid': 'Zero',
    'client_password': 'password',
    'lora_channel': 7,
    'lora_freq': 868.125,
    'lora_net_id': '0x1234'
}

def read_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return dict(CONFIG_DEFAULTS)

def write_config(data):
    cfg = read_config()
    cfg.update(data)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send', methods=['POST'])
def send():
    target = int(request.form['target'], 16)
    msg = request.form['message'].encode()
    node.send_mesh(target, msg)
    message_history.append({
        'timestamp': time.strftime('%H:%M:%S'),
        'from': 'Me',
        'to': hex(target),
        'payload': request.form['message'],
        'rssi': None,
        'outgoing': True
    })
    return jsonify({'status': 'sent'})

@app.route('/recv')
def recv():
    result = node.recv_mesh()
    if result:
        addr, payload, rssi = result
        connected_devices[addr] = {'addr': hex(addr), 'rssi': rssi}
        text = payload.decode(errors='ignore')
        message_history.append({
            'timestamp': time.strftime('%H:%M:%S'),
            'from': hex(addr),
            'to': 'Me',
            'payload': text,
            'rssi': rssi,
            'outgoing': False
        })
        return jsonify({'from': hex(addr), 'payload': text, 'rssi': rssi})
    return jsonify({'status': 'no data'})

@app.route('/devices')
def devices():
    return jsonify({'devices': list(connected_devices.values())})

@app.route('/history')
def history():
    return jsonify({'messages': message_history[-50:]})

@app.route('/config', methods=['GET'])
def get_config():
    return jsonify(read_config())

@app.route('/config', methods=['POST'])
def post_config():
    data = request.get_json(force=True)
    allowed = {'ap_ssid', 'ap_password', 'client_ssid', 'client_password',
                'lora_channel', 'lora_freq', 'lora_net_id'}
    filtered = {k: v for k, v in data.items() if k in allowed}
    if not filtered:
        return jsonify({'status': 'error', 'message': 'No valid keys provided'}), 400
    # Basic validation
    if 'lora_channel' in filtered:
        filtered['lora_channel'] = int(filtered['lora_channel'])
    if 'lora_freq' in filtered:
        filtered['lora_freq'] = float(filtered['lora_freq'])
    write_config(filtered)
    return jsonify({'status': 'saved'})

@app.route('/update', methods=['POST'])
def update():
    try:
        subprocess.Popen(['sudo', 'bash', '/home/zero/LoRa-Test/setup_wifi_ap.sh'])
        return jsonify({'status': 'Updating and rebooting...'}), 202
    except Exception as e:
        return jsonify({'status': f'Update failed: {e}'}), 500

@app.route('/reboot', methods=['POST'])
def reboot():
    try:
        subprocess.Popen(['sudo', 'reboot'])
        return jsonify({'status': 'Rebooting...'}), 202
    except Exception as e:
        return jsonify({'status': f'Reboot failed: {e}'}), 500

def run_dashboard():
    import socket
    hostname = socket.gethostname()
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    threading.Thread(target=run_dashboard).start()
