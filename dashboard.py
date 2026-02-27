
from flask import Flask, render_template_string
import json
from utils import get_wifi_clients

NODE_STATUS_FILE = 'lora_nodes.json'

app = Flask(__name__)

def get_lora_nodes():
        try:
                with open(NODE_STATUS_FILE) as f:
                        nodes = json.load(f)
                        return [
                                {'addr': addr, 'last_seen': info['last_seen'], 'ip': info.get('ip', 'N/A')}
                                for addr, info in nodes.items()
                        ]
        except Exception:
                return []

@app.route('/')
def dashboard():
        wifi_clients = get_wifi_clients()
        lora_nodes = get_lora_nodes()
        return render_template_string("""
        <!DOCTYPE html>
        <html lang='de'>
        <head>
            <meta charset='UTF-8'>
            <meta name='viewport' content='width=device-width, initial-scale=1'>
            <title>LoRa Node Dashboard</title>
            <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css' rel='stylesheet'>
            <link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'>
            <style>
                body { background: #f8fafc; }
                .dashboard-header { margin-top: 2rem; margin-bottom: 2rem; }
                .card { margin-bottom: 1rem; }
                .icon { font-size: 1.5rem; margin-right: 0.5rem; }
            </style>
        </head>
        <body>
            <div class='container'>
                <div class='dashboard-header text-center'>
                    <h1><i class='fa-solid fa-satellite-dish'></i> LoRa Node Dashboard</h1>
                    <p class='text-muted'>Statusübersicht aller verbundenen Geräte</p>
                </div>
                <div class='row'>
                    <div class='col-md-6'>
                        <div class='card shadow-sm'>
                            <div class='card-header bg-primary text-white'>
                                <i class='fa-solid fa-wifi icon'></i> WLAN Clients
                            </div>
                            <ul class='list-group list-group-flush'>
                                {% for c in wifi_clients %}
                                    <li class='list-group-item'>
                                        <i class='fa-solid fa-mobile-screen'></i> <strong>{{c.ip}}</strong> <span class='text-muted'>(MAC: {{c.mac}})</span>
                                    </li>
                                {% else %}
                                    <li class='list-group-item text-muted'>Keine Clients verbunden</li>
                                {% endfor %}
                            </ul>
                        </div>
                    </div>
                    <div class='col-md-6'>
                        <div class='card shadow-sm'>
                            <div class='card-header bg-success text-white'>
                                <i class='fa-solid fa-tower-broadcast icon'></i> LoRa Nodes
                            </div>
                            <ul class='list-group list-group-flush'>
                                {% for n in lora_nodes %}
                                    <li class='list-group-item'>
                                        <i class='fa-solid fa-microchip'></i> <strong>Addr:</strong> {{n.addr}} <span class='ms-2'><strong>IP:</strong> {{n.ip}}</span> <span class='ms-2 text-muted'><strong>Last seen:</strong> {{n.last_seen}}</span>
                                    </li>
                                {% else %}
                                    <li class='list-group-item text-muted'>Keine LoRa-Nodes verbunden</li>
                                {% endfor %}
                            </ul>
                        </div>
                    </div>
                </div>
                <footer class='text-center mt-4 mb-2 text-muted'>
                    <small>&copy; 2026 LoRa-Test | Powered by Flask & Bootstrap</small>
                </footer>
            </div>
            <script src='https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js'></script>
        </body>
        </html>
        """, wifi_clients=wifi_clients, lora_nodes=lora_nodes)

if __name__ == '__main__':
        app.run(host='0.0.0.0', port=80)
