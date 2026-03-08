from flask import Flask, render_template, request, jsonify
import threading
import subprocess
import time
import json
import os

from .node import LoRaMeshNode, PKT_JOIN, PKT_ACK, PKT_BEACON, PKT_MSG

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------
CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'lora_config.json'
)
CONFIG_DEFAULTS = {
    'ap_ssid':        'ZeroLora',
    'ap_password':    'loramesh123',
    'client_ssid':    'Zero',
    'client_password':'password',
    'lora_channel':   7,
    'lora_freq':      868.125,
    'lora_net_id':    '0',
    'tx_power':       22,         # dBm
    'air_rate':       2.4,        # kbps
    'encryption':     False,
    'debug':          False,
}

def read_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
    else:
        cfg = dict(CONFIG_DEFAULTS)
    # Automatisch lora_net_id aus Hostname setzen, falls nicht vorhanden oder leer
    import socket, hashlib
    changed = False
    if not cfg.get('lora_net_id') or str(cfg.get('lora_net_id')).strip() in ('', '0', '0x0'):
        hostname = socket.gethostname()
        lora_id = hex(int(hashlib.sha256(hostname.encode()).hexdigest()[:4], 16))
        cfg['lora_net_id'] = lora_id
        changed = True
    # Frequenz validieren: nur 868.0 oder 868.125 zulassen
    freq = float(cfg.get('lora_freq', 868.125))
    if abs(freq - 868.0) > 0.2 and abs(freq - 868.125) > 0.2:
        cfg['lora_freq'] = 868.125
        changed = True
    if changed:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(cfg, f, indent=2)
    return cfg

def write_config(data):
    cfg = read_config()
    cfg.update(data)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=2)

# ---------------------------------------------------------------------------
# LoRa node (initialised from lora_config.json)
# ---------------------------------------------------------------------------
def _init_node():
    cfg    = read_config()
    raw_id = cfg.get('lora_net_id', '0')
    net_id = int(raw_id, 16) if isinstance(raw_id, str) else int(raw_id)
    freq   = float(cfg.get('lora_freq', 868.0))
    return LoRaMeshNode(net_id=net_id, freq=freq)

app  = Flask(__name__)
node = _init_node()
node.config_mesh()

# In-memory state
connected_devices = {}
message_history   = []
_history_lock     = threading.Lock()

# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send', methods=['POST'])
def send():
    try:
        target = int(request.form['target'], 16)
        msg    = request.form['message']
        node.send_message(target, msg)
        with _history_lock:
            message_history.append({
                'timestamp': time.strftime('%H:%M:%S'),
                'from':      'Me',
                'to':        hex(target),
                'payload':   msg,
                'rssi':      None,
                'outgoing':  True,
            })
        return jsonify({'status': 'sent'})
    except Exception as e:
        return jsonify({'status': f'error: {e}'}), 500

@app.route('/recv')
def recv():
    with _history_lock:
        incoming = [m for m in message_history if not m['outgoing']]
    if incoming:
        last = incoming[-1]
        return jsonify({'from': last['from'], 'payload': last['payload'], 'rssi': last['rssi']})
    return jsonify({'status': 'no data'})

@app.route('/devices')
def devices():
    return jsonify({'devices': list(connected_devices.values())})

@app.route('/mesh')
def mesh_view():
    """Full mesh network table including each node''s WiFi clients."""
    return jsonify({'mesh': list(node.mesh_table.values())})

@app.route('/history')
def history():
    with _history_lock:
        msgs = list(message_history[-50:])
    return jsonify({'messages': msgs})

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

# ---------------------------------------------------------------------------
# Background thread: receive loop + periodic beacon
# ---------------------------------------------------------------------------
def _recv_loop():
    """Reads LoRa packets, handles handshake, buffers chat messages."""
    _last_beacon = time.time()
    while True:
        try:
            result = node.recv_mesh()
            if result:
                pkt_type, data, rssi, src = result
                if pkt_type == PKT_JOIN:
                    node.send_ack(src)
                elif pkt_type == PKT_MSG:
                    text = data.get('text', '')
                    with _history_lock:
                        connected_devices[hex(src)] = {
                            'addr':     hex(src),
                            'rssi':     rssi,
                            'hostname': data.get('host', '?'),
                        }
                        message_history.append({
                            'timestamp': time.strftime('%H:%M:%S'),
                            'from':      hex(src),
                            'to':        'Me',
                            'payload':   text,
                            'rssi':      rssi,
                            'outgoing':  False,
                        })
                # PKT_ACK / PKT_BEACON: mesh_table already updated inside recv_mesh()
        except Exception:
            pass

        if time.time() - _last_beacon >= 30:
            try:
                node.broadcast_beacon()
            except Exception:
                pass
            _last_beacon = time.time()

        time.sleep(0.3)

# Start background thread and announce ourselves on the mesh
threading.Thread(target=_recv_loop, daemon=True).start()
try:
    node.broadcast_join()
except Exception:
    pass


def run_dashboard():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    run_dashboard()
