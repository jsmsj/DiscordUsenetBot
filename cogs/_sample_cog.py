"""Imports"""
import discord
from discord.ext import commands

class General(commands.Cog):
    """General commands"""

    def __init__(self, bot):
        self.bot:commands.Bot = bot

    async def cog_before_invoke(self, ctx):
        """
        Triggers typing indicator on Discord before every command.
        """
        await ctx.channel.typing()    
        return

    @commands.command()
    async def cmd(self,ctx):
        ...


async def setup(bot):
    await bot.add_cog(General(bot))
    print("General cog is loaded")