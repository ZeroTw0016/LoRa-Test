import hmac, hashlib, struct, time
from datetime import datetime

NETWORK_SECRET = b"ZeroLoRaMasterSecret2026!"  # CHANGE THIS ON ALL NODES!

class RollingLoRaSecurity:
    @staticmethod
    def get_daily_secret():
        date_str = datetime.now().strftime("%Y-%m-%d").encode()
        return hmac.new(NETWORK_SECRET, date_str, hashlib.sha256).digest()

    @staticmethod
    def authenticate_packet(src_addr, timestamp, payload):
        daily_secret = RollingLoRaSecurity.get_daily_secret()
        expected = hmac.new(daily_secret,
            struct.pack('>HI', src_addr, timestamp) + payload[:-4],
            hashlib.sha256).digest()[:4]
        return expected == payload[-4:]

    @staticmethod
    def sign_packet(dest_addr, payload):
        daily_secret = RollingLoRaSecurity.get_daily_secret()
        timestamp = int(time.time())
        sig_data = struct.pack('>HI', dest_addr, timestamp) + payload
        hmac_sig = hmac.new(daily_secret, sig_data, hashlib.sha256).digest()[:4]
        return struct.pack('>HI', dest_addr, timestamp) + payload + hmac_sig
