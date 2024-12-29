import random
import string
from colorama import Fore, init

# Initialize colorama
init()

# Get target, host, and port from user input
target = input(f"{Fore.RED}Enter target domain (e.g., google.com): {Fore.RESET}")
host = input(f"{Fore.RED}Enter host (default: 127.0.0.1): {Fore.RESET}") or "127.0.0.1"
port = int(input(f"{Fore.RED}Enter port (default: 8080): {Fore.RESET}") or "8080")

print(f"""
{Fore.RED}╔══════════════════════════════════════════╗
║             Rusu's MITM Proxy            ║
╠══════════════════════════════════════════╣
║ Target: {target:<32} ║
║ Host: {host:<34} ║
║ Port: {str(port):<34} ║
╚══════════════════════════════════════════╝{Fore.RESET}
""")

secret = ''.join(random.choice(string.ascii_letters + string.digits + '-' + '_' + '@') for _ in range(random.randint(1, 2))) # original 32, 75
# secret = 'or whatever you want, but make sure it is a valid path and is secure'
print(f"\n{Fore.RESET}Your panel is available at {Fore.RED}http://{host}:{port}/{secret}{Fore.RESET}.")

print(Fore.RESET)

# Import the start_proxy function from the local server.py
from server import start_proxy

# Start the proxy with the configured parameters
start_proxy(target, host, port, secret)