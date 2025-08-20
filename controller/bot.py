import asyncio
import discord
from discord.ext import commands
from controller.controllers import load_controllers
import json
import os


class ControllerBot(commands.Bot):
    """Main bot class that initializes the bot and loads controllers."""
    def __init__(self, token, log_message, register_commands=True, load_settings_flag=True):
        intents = discord.Intents.default()
        intents.message_content = True

        self.settings = {
            "default_prefix": "!"
        }

        super().__init__(
            command_prefix=lambda bot, msg: bot.settings.get("default_prefix", "!"),
            intents=intents
        )

        self.token = token
        self.log_message = log_message
        self._controllers = []  
        self._should_register_commands = register_commands

        load_controllers(self)
        self.controllers = [type(c).__name__ for c in self._controllers]

        if load_settings_flag:
            self.load_settings()


    async def setup_hook(self):
        """Setup hook called when the bot is ready to start."""
        if self._should_register_commands and hasattr(self, "register_commands"):
            rc = self.register_commands()
            if asyncio.iscoroutine(rc):
                await rc

    async def on_ready(self):
        """Event called when the bot is ready."""
        self.log_message(f"✅ Bot started as {self.user}")

    @staticmethod
    def get_default_settings():
        """Return default settings for the bot."""
        return {"default_prefix": "!"}
    
    def load_settings(self):
        """Load settings from a JSON file."""    
        try:
            if os.path.exists("settings.json"):
                with open("settings.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.settings.update(data.get("ControllerBot", {}))
        except Exception as e:
            self.log_message(f"Error loading bot settings: {str(e)}")

    def save_settings(self):
        """Save the current settings to a JSON file."""
        try:
            data = {}
            if os.path.exists("settings.json"):
                with open("settings.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["ControllerBot"] = self.settings
            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            self.log_message("Bot settings saved")
        except Exception as e:
            self.log_message(f"Error saving bot settings: {str(e)}")
