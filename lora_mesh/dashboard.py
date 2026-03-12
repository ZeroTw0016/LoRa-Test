from flask import Flask, render_template, request, jsonify
import threading
import subprocess
import time
import json
import os
import logging
from collections import deque

from .node import LoRaMeshNode, PKT_JOIN, PKT_ACK, PKT_BEACON, PKT_MSG

# ---------------------------------------------------------------------------
# In-memory log buffer (last 300 lines)
# ---------------------------------------------------------------------------
_log_buffer = deque(maxlen=300)
_log_lock   = threading.Lock()

class _DequeHandler(logging.Handler):
    def emit(self, record):
        line = self.format(record)
        with _log_lock:
            _log_buffer.append(line)

_handler = _DequeHandler()
_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s',
                                        datefmt='%H:%M:%S'))
logging.root.addHandler(_handler)
logging.root.setLevel(logging.INFO)
log = logging.getLogger(__name__)

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
    # Automatisch ap_ssid und lora_net_id aus Hostname setzen, falls nicht vorhanden oder leer
    import socket, hashlib
    changed = False
    hostname = socket.gethostname()
    if not cfg.get('ap_ssid') or cfg.get('ap_ssid') == 'ZeroLora':
        cfg['ap_ssid'] = hostname
        changed = True
    if not cfg.get('lora_net_id') or str(cfg.get('lora_net_id')).strip() in ('', '0', '0x0'):
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
try:
    node = _init_node()
    node.config_mesh()
    log.info('LoRa hardware initialised successfully.')
except Exception as _hw_err:
    import sys
    log.warning(f'LoRa hardware init failed: {_hw_err}')
    print(f'WARNING: LoRa hardware init failed: {_hw_err}', file=sys.stderr)
    node = None

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
    """Full mesh network table including each node's WiFi clients."""
    if node is None:
        return jsonify({'mesh': []})
    return jsonify({'mesh': list(node.mesh_table.values())})

@app.route('/history')
def history():
    with _history_lock:
        msgs = list(message_history[-50:])
    return jsonify({'messages': msgs})

@app.route('/logs')
def get_logs():
    with _log_lock:
        lines = list(_log_buffer)
    # also try journalctl for older entries
    try:
        out = subprocess.check_output(
            ['journalctl', '-u', 'lora_mesh_dashboard.service',
             '-n', '100', '--no-pager', '--output=short'],
            stderr=subprocess.DEVNULL, timeout=3
        ).decode(errors='replace')
        jlines = [l for l in out.splitlines() if l.strip()]
    except Exception:
        jlines = []
    return jsonify({'logs': jlines + lines})


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
        if node is None:
            time.sleep(5)
            continue
        try:
            result = node.recv_mesh()
            if result:
                pkt_type, data, rssi, src = result
                log.info(f'RX pkt_type={pkt_type:#04x} src={src:#06x} rssi={rssi}')
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
                log.debug('Beacon sent.')
            except Exception:
                pass
            _last_beacon = time.time()

        time.sleep(0.3)

# Start background thread and announce ourselves on the mesh
threading.Thread(target=_recv_loop, daemon=True).start()
if node is not None:
    try:
        node.broadcast_join()
        log.info('Join beacon broadcast.')
    except Exception:
        pass

log.info('Dashboard running on http://0.0.0.0:5000')


def run_dashboard():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    run_dashboard()
