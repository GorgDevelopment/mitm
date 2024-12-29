import re
import requests
from typing import Dict, List, Optional

class DataDetector:
    def __init__(self):
        # Credit card pattern (supports major card formats)
        self.cc_pattern = re.compile(
            r'\b(?:'
            r'4[0-9]{12}(?:[0-9]{3})?|'  # Visa
            r'5[1-5][0-9]{14}|'           # MasterCard
            r'3[47][0-9]{13}|'            # American Express
            r'3(?:0[0-5]|[68][0-9])[0-9]{11}|'  # Diners Club
            r'6(?:011|5[0-9]{2})[0-9]{12}|'     # Discover
            r'(?:2131|1800|35\d{3})\d{11}'      # JCB
            r')\b'
        )
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.password_fields = ['password', 'pass', 'pwd', 'secret']

    def scan_form_data(self, form_data: Dict) -> Dict[str, str]:
        """Scan form data for sensitive information"""
        results = {}
        
        # Check for passwords
        for key, value in form_data.items():
            if any(pwd in key.lower() for pwd in self.password_fields):
                results['password'] = value
            
            # Check for credit cards in value
            if cc_numbers := self.detect_credit_cards(str(value)):
                results['credit_card'] = cc_numbers[0]
            
            # Check for emails in value
            if emails := self.detect_emails(str(value)):
                results['email'] = emails[0]
        
        return results

    def detect_credit_cards(self, text: str) -> List[str]:
        """Detect and validate credit card numbers"""
        matches = self.cc_pattern.findall(text)
        return [card for card in matches if self.is_valid_card(card)]

    def detect_emails(self, text: str) -> List[str]:
        """Detect email addresses"""
        return self.email_pattern.findall(text)

    @staticmethod
    def is_valid_card(card: str) -> bool:
        """Validate credit card using Luhn algorithm"""
        card = card.replace(' ', '')
        if not card.isdigit():
            return False
            
        digits = [int(d) for d in card]
        checksum = digits.pop()
        digits.reverse()
        
        total = sum(
            sum(divmod(d * 2, 10)) if i % 2 == 0 else d
            for i, d in enumerate(digits)
        )
        
        return (total + checksum) % 10 == 0

    def get_geolocation(self, ip: str) -> Optional[Dict]:
        """Get geolocation data for an IP address"""
        try:
            response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'ip': ip,
                    'country': data.get('country'),
                    'city': data.get('city'),
                    'lat': data.get('lat'),
                    'lon': data.get('lon'),
                    'isp': data.get('isp'),
                    'org': data.get('org')
                }
        except Exception as e:
            print(f"Geolocation error: {str(e)}")
        return None
