from flask import Flask, render_template, request, jsonify
import threading
from .node import LoRaMeshNode

app = Flask(__name__)
node = LoRaMeshNode()
node.config_mesh()

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
        return jsonify({'from': hex(addr), 'payload': payload.decode(errors='ignore'), 'rssi': rssi})
    return jsonify({'status': 'no data'})

def run_dashboard():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    threading.Thread(target=run_dashboard).start()
