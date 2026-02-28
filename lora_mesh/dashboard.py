from flask import Flask, render_template, request, jsonify
import threading
from .node import LoRaMeshNode

app = Flask(__name__)
node = LoRaMeshNode()
node.config_mesh()

# Store seen devices in memory (for demo)
connected_devices = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send', methods=['POST'])
def send():
    target = int(request.form['target'], 16)
    msg = request.form['message'].encode()
    node.send_mesh(target, msg)
    return jsonify({'status': 'sent'})

@app.route('/recv')
def recv():
    result = node.recv_mesh()
    if result:
        addr, payload, rssi = result
        # Track device
        connected_devices[addr] = {'addr': hex(addr), 'rssi': rssi}
        return jsonify({'from': hex(addr), 'payload': payload.decode(errors='ignore'), 'rssi': rssi})
    return jsonify({'status': 'no data'})

@app.route('/devices')
def devices():
    # Return all seen devices
    return jsonify({'devices': list(connected_devices.values())})

def run_dashboard():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    threading.Thread(target=run_dashboard).start()
