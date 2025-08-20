from discord.ext import commands
import json
import os

class ControllerPing:
    """Controller for handling ping commands."""
    def __init__(self, bot, register_commands=True, load_settings_flag=True):
        self.bot = bot
        self.settings = {
            "enabled": True,
            "response": "Pong!",
            "response2": "Ping successful!"}
        if load_settings_flag:
            self.load_settings()
        if register_commands:
            self.register_commands()
    @staticmethod
    def get_default_settings():
        return {
            "enabled": True,
            "response": "Pong!",
            "response2": "Ping successful!"
        }

    def load_settings(self):
        try:
            if os.path.exists("settings.json"):
                with open("settings.json", "r") as f:
                    data = json.load(f)
                    self.settings.update(data.get("ControllerPing", {}))
        except Exception as e:
            self.bot.log_message(f"Error loading ping settings: {str(e)}")

    def save_settings(self):
        try:
            data = {}
            if os.path.exists("settings.json"):
                with open("settings.json", "r") as f:
                    data = json.load(f)
            data["ControllerPing"] = self.settings
            with open("settings.json", "w") as f:
                json.dump(data, f, indent=4)
            self.bot.log_message("Ping settings saved")
        except Exception as e:
            self.bot.log_message(f"Error saving ping settings: {str(e)}")

    def register_commands(self):
        if not self.settings["enabled"]:
            return

        @self.bot.command(name="ping")
        async def ping(ctx):
            await ctx.send(self.settings["response"])
            await ctx.send(self.settings["response2"])