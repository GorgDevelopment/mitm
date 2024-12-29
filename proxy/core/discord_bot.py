import discord
from discord.ext import commands
import json
import os
import threading
import requests
from datetime import datetime
from colorama import Fore

class DiscordBot:
    def __init__(self, webhook_url, token):
        print(f"{Fore.YELLOW}[*] Initializing Discord bot...{Fore.RESET}")
        self.webhook_url = webhook_url
        self.token = token
        self.bot = None
        self.bot_thread = None
        self.running = True
        self.start()

    def start(self):
        try:
            intents = discord.Intents.all()
            self.bot = commands.Bot(command_prefix='/', intents=intents)
            self.setup_commands()
            
            self.bot_thread = threading.Thread(target=self.run_bot)
            self.bot_thread.daemon = True
            self.bot_thread.start()
            
            print(f"{Fore.GREEN}[+] Discord bot started successfully{Fore.RESET}")
        except Exception as e:
            print(f"{Fore.RED}[!] Failed to start Discord bot: {str(e)}{Fore.RESET}")
            raise

    def stop(self):
        print(f"{Fore.YELLOW}[*] Stopping Discord bot...{Fore.RESET}")
        self.running = False
        if self.bot:
            try:
                self.bot.close()
            except:
                pass
        if self.bot_thread:
            try:
                self.bot_thread.join(timeout=1)
            except:
                pass
        print(f"{Fore.GREEN}[+] Discord bot stopped{Fore.RESET}")

    def run_bot(self):
        try:
            self.bot.run(self.token)
        except Exception as e:
            print(f"{Fore.RED}[!] Bot runtime error: {str(e)}{Fore.RESET}")

    def setup_commands(self):
        @self.bot.event
        async def on_ready():
            print(f"{Fore.GREEN}[+] Logged in as {self.bot.user.name}#{self.bot.user.discriminator}{Fore.RESET}")
            try:
                await self.bot.tree.sync()
                print(f"{Fore.GREEN}[+] Command tree synced{Fore.RESET}")
            except Exception as e:
                print(f"{Fore.RED}[!] Failed to sync commands: {str(e)}{Fore.RESET}")

        # ... rest of your commands ...

    def send_webhook(self, data):
        try:
            response = requests.post(self.webhook_url, json=data)
            if response.status_code != 204:
                print(f"{Fore.RED}[!] Webhook error: {response.status_code}{Fore.RESET}")
        except Exception as e:
            print(f"{Fore.RED}[!] Failed to send webhook: {str(e)}{Fore.RESET}")
