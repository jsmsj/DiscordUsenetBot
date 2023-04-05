import logging
from discord.ext import commands
import discord
import os
import cogs._config
import os,sys
from cogs._helpers import embed,check_before_starting,sudo_check
import traceback
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import datetime
from loggerfile import logger

intents = discord.Intents.all()

bot = commands.Bot(command_prefix=cogs._config.prefix, intents=intents, case_insensitive=True) 

logger.info("Starting Apscheduler...")
scheduler = AsyncIOScheduler()
scheduler.start()

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Usenet x Discord"))
    print("Bot is ready!")

@bot.event
async def on_command_error(ctx:commands.Context,error):
    if hasattr(ctx.command, 'on_error'):
        return
    if isinstance(error,commands.CommandNotFound):
        return
    if isinstance(error,commands.CheckFailure):
        logger.info(f'{ctx.author.name} ({ctx.author.id}) ran {ctx.command.name} but was unable to run it due to checkfailure.')
        return await ctx.send('Cannot use this command here.... or you are not authorised to run this command.')
    else:
        logger.warning(error,exc_info=True)
        logger.warning(traceback.format_exc())
        _file=None
        if os.path.exists('log.txt'):
            _file = discord.File('log.txt')
        await ctx.send(embed=embed(f'Error | {ctx.command.name}',f'An error occured.\n```py\n{error}\n```\nHere is the attached logfile.')[0],file=_file)

@bot.command(description="Shows the bot's latency")
async def ping(ctx):
    await ctx.send(f"🏓 {round(bot.latency*1000)}ms")


@sudo_check()
@bot.command(description='logfile')
async def log(ctx):
    if os.path.exists('log.txt'):
        await ctx.send(embed=embed('📃 Log File','Here is the log file')[0],file=discord.File('log.txt'))
    else:
        await ctx.send(embed=embed('📃 Log File','No logfile found :(')[0])



async def run_main():
    for file in os.listdir("cogs/"):
        if file.endswith(".py") and not file.startswith("_"):
            await bot.load_extension(f"cogs.{file[:-3]}")
    
    await bot.load_extension('jishaku')
    # CHECKS:
    logger.info('Cheking SABNZBD config....')
    try:
        check_before_starting('sabnzbd')
    except:
        logger.critical(
            "Can not establish a successful connection with SABnzbd. Please double-check your configs and try again later.")
        sys.exit(1)
    logger.info('Cheking NZBHydra config....')
    try:
        check_before_starting('nzbhydra')
    except Exception as error:
        print(error)
        logger.critical(
            "Can not establish a successful connection with NZBHydra. Please double-check your configs and try again later.")
        sys.exit(1)
    logger.info('All checks passed...')

    await bot.start(cogs._config.bot_token)
    logger.info("Bot has started, all cogs are loaded.")

BotStartTime = datetime.datetime.utcnow()
if __name__ == '__main__':
    # When running this file, if it is the 'main' file
    # i.e. its not being imported from another python file run this
    asyncio.run(run_main())
