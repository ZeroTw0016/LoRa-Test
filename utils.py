import os

def get_wifi_clients():
    clients = []
    try:
        with open('/var/lib/misc/dnsmasq.leases') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 3:
                    clients.append({'ip': parts[2], 'mac': parts[1]})
    except Exception:
        pass
    return clients

