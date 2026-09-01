import os
import threading
import discord
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask

load_dotenv()

BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]

flask_app = Flask('')

@flask_app.route('/')
def home():
    return "Bot status operational"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

class CodeEditorBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Dynamically imports and links your new editor logic module
        await self.load_extension("editor_cog")
        await self.tree.sync()

bot = CodeEditorBot()

@bot.event
async def on_ready():
    print(f"Bot online as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Global Sync Complete! {len(synced)} root nodes deployed.")
    except Exception as e:
        print(f"Clean Sync Failed: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.run(BOT_TOKEN)
