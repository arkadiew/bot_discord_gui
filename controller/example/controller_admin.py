from discord.ext import commands
import discord
import json
import os

class ControllerAdmin:
    """Controller for handling administrative commands."""
    def __init__(self, bot, register_commands=True, load_settings_flag=True):
        self.bot = bot
        self.settings = {
            "ban_enabled": True,
            "kick_enabled": True,
            "mute_enabled": True,
            "default_ban_reason": "No reason provided",
            "default_mute_role": "Muted",
            "default_mute_duration": 60  
        }
        if load_settings_flag:
            self.load_settings()
        if register_commands:
            self.register_commands()
    @staticmethod
    def get_default_settings():
        return {
            "ban_enabled": True,
            "kick_enabled": True,
            "mute_enabled": True,
            "default_ban_reason": "No reason provided",
            "default_mute_role": "Muted",
            "default_mute_duration": 60
        }

    def load_settings(self):
        try:
            if os.path.exists("settings.json"):
                with open("settings.json", "r") as f:
                    data = json.load(f)
                    self.settings.update(data.get("ControllerAdmin", {}))
        except Exception as e:
            self.bot.log_message(f"Error loading admin settings: {str(e)}")

    def save_settings(self):
        try:
            data = {}
            if os.path.exists("settings.json"):
                with open("settings.json", "r") as f:
                    data = json.load(f)
            data["ControllerAdmin"] = self.settings
            with open("settings.json", "w") as f:
                json.dump(data, f, indent=4)
            self.bot.log_message("Admin settings saved")
        except Exception as e:
            self.bot.log_message(f"Error saving admin settings: {str(e)}")

    @staticmethod
    def is_admin():
        def predicate(ctx):
            return ctx.author.guild_permissions.administrator
        return commands.check(predicate)

    def register_commands(self):
        if self.settings["ban_enabled"]:
            @self.bot.command(name="ban")
            @ControllerAdmin.is_admin()
            async def ban(ctx, member: discord.Member, *, reason=None):
                try:
                    reason = reason or self.settings["default_ban_reason"]
                    await member.ban(reason=reason)
                    await ctx.send(f"🔨 {member.mention} has been banned. Reason: {reason}")
                except Exception as e:
                    await ctx.send(f"❌ Failed to ban: {e}")

        if self.settings["kick_enabled"]:
            @self.bot.command(name="kick")
            @ControllerAdmin.is_admin()
            async def kick(ctx, member: discord.Member, *, reason):
                try:
                    await member.kick(reason=reason)
                    await ctx.send(f"👢 {member.mention} has been kicked. Reason: {reason}")
                except Exception as e:
                    await ctx.send(f"❌ Failed to kick: {e}")

        if self.settings["mute_enabled"]:
            @self.bot.command(name="mute")
            @ControllerAdmin.is_admin()
            async def mute(ctx, member: discord.Member, *, reason=None):
                guild = ctx.guild
                muted_role = discord.utils.get(guild.roles, name=self.settings["default_mute_role"])

                if not muted_role:
                    try:
                        muted_role = await guild.create_role(name=self.settings["default_mute_role"])
                        for channel in guild.channels:
                            await channel.set_permissions(
                                muted_role,
                                send_messages=False,
                                speak=False,
                                read_messages=True,
                                read_message_history=True
                            )
                    except Exception as e:
                        return await ctx.send(f"❌ Failed to create Muted role: {e}")

                try:
                    await member.add_roles(muted_role, reason=reason or self.settings["default_ban_reason"])
                    await ctx.send(f"🔇 {member.mention} has been muted for {self.settings['default_mute_duration']} minutes. Reason: {reason}")
                except Exception as e:
                    await ctx.send(f"❌ Failed to mute: {e}")