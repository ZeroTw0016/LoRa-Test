from flask import Flask, render_template, request, jsonify
import threading
from .node import LoRaMeshNode
import time
import subprocess

app = Flask(__name__)
node = LoRaMeshNode()
node.config_mesh()

# ...existing code...

# Update and reboot endpoint
@app.route('/update', methods=['POST'])
def update():
    # Run setup_wifi_ap.sh and reboot
    try:
        subprocess.Popen(['sudo', 'bash', 'setup_wifi_ap.sh'])
        return jsonify({'status': 'Updating and rebooting...'}), 202
    except Exception as e:
        return jsonify({'status': f'Update failed: {e}'}), 500
from flask import Flask, render_template, request, jsonify
import threading
from .node import LoRaMeshNode
import time

app = Flask(__name__)
node = LoRaMeshNode()
node.config_mesh()

# Store seen devices and message history in memory
connected_devices = {}
message_history = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send', methods=['POST'])
def send():
    target = int(request.form['target'], 16)
    msg = request.form['message'].encode()
    node.send_mesh(target, msg)
    # Add to history as outgoing message
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
        # Add to history as incoming message
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
    # Return last 50 messages
    return jsonify({'messages': message_history[-50:]})

def run_dashboard():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    threading.Thread(target=run_dashboard).start()
