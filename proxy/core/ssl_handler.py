from OpenSSL import crypto
import os
from datetime import datetime, timedelta
from pathlib import Path

class SSLHandler:
    def __init__(self):
        self.cert_dir = Path("certs")
        self.cert_dir.mkdir(exist_ok=True)
        
        self.key_path = self.cert_dir / "proxy.key"
        self.cert_path = self.cert_dir / "proxy.crt"
        
        if not (self.key_path.exists() and self.cert_path.exists()):
            self.generate_cert()

    def generate_cert(self):
        # Generate key
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)
        
        # Generate certificate
        cert = crypto.X509()
        cert.get_subject().CN = "Rusu's MITM Proxy"
        cert.get_subject().O = "Rusu Security"
        cert.get_subject().OU = "Proxy Division"
        
        cert.set_serial_number(int(datetime.now().timestamp()))
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(365*24*60*60)  # Valid for 1 year
        
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(key)
        cert.sign(key, 'sha256')
        
        # Save certificate and private key
        with open(self.cert_path, "wb") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
            
        with open(self.key_path, "wb") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))

    def get_cert_paths(self):
        return {
            'certfile': str(self.cert_path),
            'keyfile': str(self.key_path)
        }
