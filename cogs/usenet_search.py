"""Imports"""
import discord,re
from discord.ext import commands
from cogs._nzbhydra import NzbHydra
from cogs._config import *

import cogs._helpers  as hp


def cog_check():
    def predicate(ctx):
        if len(AUTHORIZED_CHANNELS_LIST) == 0:
            return True
        if ctx.message.channel.id in AUTHORIZED_CHANNELS_LIST:
            return True
        else:
            return False
    return commands.check(predicate)

class UsenetSearch(commands.Cog):
    """UsenetSearch commands"""

    def __init__(self, bot):
        self.bot:commands.Bot = bot
        self.nzbhydra = NzbHydra()


    async def cog_before_invoke(self, ctx):
        """
        Triggers typing indicator on Discord before every command.
        """
        await ctx.channel.typing()     
        return

    @commands.command()
    @cog_check()
    async def search(self,ctx:commands.Context,cmd:str=None,*,user_input:str=None):
        commands = ['nzbfind','nzbsearch','movie','movies',"series", "tv"]
        if not cmd or not cmd.lower() in commands: return await ctx.send(f'No search term provided. Correct Usage: `{ctx.prefix}search command your query` where command can be: `{" , ".join(commands)}`')
        cmd = cmd.lower()
        if not user_input: return await ctx.send(f'No search term provided. Correct Usage: `{ctx.prefix}search command your query` where command can be: `{" , ".join(commands)}`')
        msg = await ctx.send(f'Searching for `{user_input}`\nPlease wait')
        output=None
        if cmd in ["nzbfind", "nzbsearch"]:
            output = await self.nzbhydra.query_search(user_input)

        elif cmd in ["movie", "movies"]:
            if re.search("^tt[0-9]*$", user_input):
                output = await self.nzbhydra.imdb_movie_search(user_input)

            elif imdbid := re.search(r".+(tt\d+)", user_input):
                try:
                    output = await self.nzbhydra.imdb_movie_search(imdbid.group(1))
                except:
                    output = await self.nzbhydra.movie_search(user_input)

            else:
                output = await self.nzbhydra.movie_search(user_input)

        elif cmd in ["series", "tv"]:
            if re.search("^tt[0-9]*$", user_input):
                output = await self.nzbhydra.imdb_series_search(user_input)

            elif imdbid := re.search(r".+(tt\d+)", user_input):
                try:
                    output = await self.nzbhydra.imdb_series_search(imdbid.group(1))
                except:
                    output = await self.nzbhydra.series_search(user_input)

            else:
                output = await self.nzbhydra.series_search(user_input)

        if not output:
            output = 'Nothing found :('
        
            await msg.edit(content=output)
        else:
            telegraph_url = await hp.telegraph_paste(content=output)
            await msg.edit(content=f'{telegraph_url}')

    @commands.command()
    @cog_check()
    @hp.sudo_check()
    async def indexers(self,ctx:commands.Context):
        replymsg = await ctx.send("Fetching list....")
        indexers = await self.nzbhydra.list_indexers()

        if indexers:
            return await replymsg.edit(content=indexers)

        return await replymsg.edit(content="No indexers found.")

    @commands.command()
    async def temp(self,ctx,*,content):
        content = content.replace('```\n','').replace('```','')
        url = await hp.telegraph_paste(content=content)
        await ctx.send(f'{url}')

async def setup(bot):
    await bot.add_cog(UsenetSearch(bot))
    print("UsenetSearch cog is loaded")