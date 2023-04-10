"""Imports"""
import discord
import requests
from discord.ext import commands
from main import BotStartTime,scheduler
from loggerfile import logger
from cogs._helpers import SABNZBD_ENDPOINT,humantime,humanbytes,sudo_check,NZBHYDRA_ENDPOINT,NZBHYDRA_STATS_ENDPOINT,NZBHYDRA_URL_ENDPOINT,remove_private_stuff
import httpx
import psutil
import time
import datetime
import re
import aiofiles
from cogs._config import *
from cachetools import TTLCache
import asyncio

downloading_status_msgids = {} 
sabnzbd_userid_log = TTLCache(maxsize=128, ttl=600)

class UsenetHelper:
    def __init__(self) -> None:
        self.SABNZBD_API = f"{SABNZBD_ENDPOINT}&output=json"
        self.client = httpx.AsyncClient(timeout=20)


    def footer_message(self):  #TODO speed calc for footer
        # calculating system speed per seconds.
        # net_io_counters = psutil.net_io_counters()
        # bytes_sent = net_io_counters.bytes_sent
        # bytes_recv = net_io_counters.bytes_recv

        # time.sleep(1)

        # net_io_counters = psutil.net_io_counters()
        # download_speed = net_io_counters.bytes_recv - bytes_recv
        # upload_speed = net_io_counters.bytes_sent - bytes_sent

        botuptime = humantime((datetime.datetime.utcnow()-BotStartTime).total_seconds())
        # msg = f"🟢 DL: {humanbytes(download_speed)}/s 🟡 UL: {humanbytes(upload_speed)}/s | ⌚ Uptime: {botuptime}"
        msg = f"⌚ Uptime: {botuptime}"
        return msg
    
    def show_progress_still(self,percent:int,width:int=20):
        int_percent = round(percent)
        hashblocks = round((int_percent*width/100)-1)
        if hashblocks<0:
            hashblocks = 0
        return "#️⃣"* hashblocks + "▶️" + "🟦"*(width-hashblocks-1) + "🏁"

    async def downloading_status_page(self):
        """Generate status page for progress message."""

        try:
            downloading_response = await self.client.get(
                self.SABNZBD_API, params={"mode": "queue"})
            # print(downloading_response.json())
            downloading_queue_list = downloading_response.json()["queue"]["slots"]
        except:
            downloading_queue_list = []

        try:
            # print(1)
            postprocessing_response = await self.client.get(
                self.SABNZBD_API, params={"mode": "history"})
            # print(postprocessing_response.json()["history"]["slots"])
            postprocessing_queue_list = [
                slot
                for slot in postprocessing_response.json()["history"]["slots"]
                if slot["status"] not in ["Completed", "Failed"]]
            postprocessing_queue_list.reverse()
        except:
            postprocessing_queue_list = []

        # status_page = ""

        status_embed = discord.Embed(title = "📊 Status",color=discord.Color.green(),timestamp=datetime.datetime.utcnow())
        status_embed.description = ''

        if downloading_queue_list:

            status_embed.description = '**Downloading -**\n\n'

            for index, queue in enumerate(downloading_queue_list):


                file_name = queue["filename"]
                if re.search(r"(http|https)", file_name):
                    file_name = "Adding file from ID."
                status_embed.description += f'**🗂 FileName:** `{file_name}`\n\n{self.show_progress_still(int(queue["percentage"]))} {queue["percentage"]}%\n\n' \
                                            f"**{queue['sizeleft']}** remaining of **{queue['size']}**\n" \
                                            f"**Status:** {queue['status']} | **ETA:** {queue['timeleft']}\n" \
                                            f"**Task ID:** `{queue['nzo_id']}`\n━━━━━━━━━━━━━━━━━━━━\n"

                if index == 4 and len(downloading_queue_list) > 4:

                    status_embed.description += f"**+ {max(len(downloading_queue_list)-4, 0)} Ongoing Tasks...**\n\n"
                    break



        if postprocessing_queue_list:

            if status_embed.description not in ['',None]:
                status_embed.description += '━━━━━━━━━━━━━━━━━━━━\n'

            status_embed.description += "**Post Processing -**\n\n"
            for index, history in enumerate(postprocessing_queue_list):

                file_name = history["name"]
                if re.search(r"(http|https)", file_name):
                    file_name = "N/A"

                
                status_embed.description += f"**🗂 FileName :** `{file_name}`\n" \
                                            f"**Status :** `{history['status']}`\n"

                action = history.get("action_line")
                if isinstance(action, list):

                    status_embed.description += f"**Action :** ```\n{action[0]}\n```\n"

                if action and "Running script:" in action:
                    action = action.replace("Running script:", "")

                    status_embed.description += f"**Action :** ```\n{action.strip()}\n```\n"

                if index == 4 and len(postprocessing_queue_list) > 4:

                    status_embed.description+= f"\n**+ Extra Queued Task...**\n\n"
                    break
                
        if status_embed.description not in ['',None]:
            status_embed.set_footer(text=self.footer_message())


        return '',status_embed
    
    async def get_file_names(self, task_ids):
        print(f"Recieved get_file_names({task_ids})")
        file_names = []
        for task_id in task_ids:
            task = await self.get_task(task_id)
            print(f"recieved task: {task}")
            file_name = task[0]['filename']
            while (re.search(r"(http|https)", file_name)):
                await asyncio.sleep(1)
                task = await self.get_task(task_id)
                file_name = task[0]["filename"]
            if not re.search(r"(http|https)", file_name):
                file_names.append(file_name)
        print(f"File names retrieved: {file_names}")
        return file_names

    async def check_task(self, task_id):
        response = await self.client.get(
            self.SABNZBD_API, params={"mode": "queue", "nzo_ids": task_id})
        
        response = response.json()
        return bool(response["queue"]["slots"])

    async def get_task(self, task_id):
        response = await self.client.get(
            self.SABNZBD_API, params={"mode": "queue", "nzo_ids": task_id})
        
        response = response.json()
        return response["queue"]["slots"]

    async def resume_task(self, task_id):
        isValidTaskID = await self.check_task(task_id)
        if not isValidTaskID:
            return False

        response = await self.client.get(
            self.SABNZBD_API,
            params={"mode": "queue", "name": "resume", "value": task_id},
        )
        return response.json()

    async def resumeall_task(self):
        response = await self.client.get(self.SABNZBD_API, params={"mode": "resume"})
        response = response.json()
        return response["status"]
    
    async def pause_task(self, task_id):
        isValidTaskID = await self.check_task(task_id)
        if not isValidTaskID:
            return False

        response = await self.client.get(
            self.SABNZBD_API,
            params={"mode": "queue", "name": "pause", "value": task_id},
        )
        return response.json()

    async def pauseall_task(self):
        response = await self.client.get(self.SABNZBD_API, params={"mode": "pause"})
        response = response.json()
        return response["status"]

    async def delete_task(self, task_id):
        isValidTaskID = await self.check_task(task_id)
        if not isValidTaskID:
            return False

        response = await self.client.get(
            self.SABNZBD_API,
            params={"mode": "queue", "name": "delete", "value": task_id},
        )
        return response.json()
    
    async def deleteall_task(self):
        response = await self.client.get(
            self.SABNZBD_API, params={"mode": "queue", "name": "delete", "value": "all"})
        
        response = response.json()
        return response["status"]

    async def add_nzbfile(self, path_name):
        try:
            async with aiofiles.open(path_name, "rb") as file:
                nzb_content = await file.read()
        except:
            return False

        payload = {"nzbfile": (path_name.split("/")[-1], nzb_content)}
        params = {"mode": "addfile"}
        response = await self.client.post(
            self.SABNZBD_API, params=params, files=payload)
        
        return response.json()

    async def add_nzburl(self, nzburl):
        params = {"mode": "addurl", "name": nzburl}
        response = await self.client.post(self.SABNZBD_API, params=params)
        return response.json()


    async def clear_progresstask(self, status_message, msg_id,**kwargs):
        """remove job, delete message and clear dictionary of progress bar."""

        scheduler.remove_job(f"{str(msg_id)}")
        # try:
        # await status_message.delete()
        excess = ''
        if kwargs.get('jump_url'):
            excess+=f':\n[Latest Message]({kwargs.get("jump_url")})'
        
        em = discord.Embed(title='📊 Status',color=discord.Color.green())
        em.description = f'No Current Tasks or see the latest status message{excess}'
        await status_message.edit(content='',embed=em)
        # except Exception as e:
        #     pass  # passing errors like status message deleted.

        if kwargs.get('pop_dict') == False:
            return
        
        downloading_status_msgids.pop(msg_id)
    
    async def show_downloading_status(self, bot:commands.Bot,channel_id, message:discord.Message):        

        # Get the status page
        status_page,status_embed = await self.downloading_status_page()
        # print(status_embed.description)
        # print()
        # print(status_page)

        # if not status_page:
        #     # chan = await bot.fetch_channel(channel_id)
        #     # await chan.fetch_message(message)
        #     return await message.reply(content="No ongoing task currently.",mention_author=False)
        
        if status_embed.description in ['',None]:
            # chan = await bot.fetch_channel(channel_id)
            # await chan.fetch_message(message)
            return await message.reply(content="No ongoing task currently.",mention_author=False)

        # Send the status message and start the job to update the downloading status message after x interval.
        status_message = await message.reply(embed=status_embed,mention_author=False)

        # Remove previous status message and scheduled job for that chat_id
        # print(message.id)
        # print(downloading_status_msgids)
        if message.id in downloading_status_msgids:
            # print('yess')
            status_message_id = downloading_status_msgids[message.id]
            chan = await bot.fetch_channel(channel_id)
            status_message_old = await chan.fetch_message(status_message_id)
            await self.clear_progresstask(status_message_old, message.id)
        else:
            for message.id in downloading_status_msgids:
                status_message_id = downloading_status_msgids[message.id]
                chan = await bot.fetch_channel(channel_id)
                status_message_old = await chan.fetch_message(status_message_id)
                await self.clear_progresstask(status_message_old, message.id,pop_dict=False,jump_url=status_message.jump_url)
            
            downloading_status_msgids.clear()
        
        downloading_status_msgids[message.id] = status_message.id

        async def edit_status_message():
            """Edit the status message  after x seconds."""

            status_page,status_embed = await self.downloading_status_page()
            # if not status_page:
            #     return await self.clear_progresstask(status_message, message.id)


            if status_embed.description in ['',None]:
                return await self.clear_progresstask(status_message, message.id)

            try:
                await status_message.edit(content=status_page,embed=status_embed)
            except Exception as e:
                logger.warn('edit_status_msg_exception\n'+str(e))
                await self.clear_progresstask(status_message, message.id)

        scheduler.add_job(
            edit_status_message,
            "interval",
            seconds=10,
            misfire_grace_time=15,
            max_instances=2,
            id=f"{str(message.id)}")
        

def cog_check():
    def predicate(ctx):
        if len(AUTHORIZED_CHANNELS_LIST) == 0:
            return True
        if ctx.message.channel.id in AUTHORIZED_CHANNELS_LIST:
            return True
        else:
            return False
    return commands.check(predicate)


class Usenet(commands.Cog):
    """Usenet commands"""

    def __init__(self, bot):
        self.bot:commands.Bot = bot
        self.usenetbot = UsenetHelper()

    async def cog_before_invoke(self, ctx):
        """
        Triggers typing indicator on Discord before every command.
        """
        await ctx.channel.typing()    
        return

    @commands.command(name='status',aliases=['dstatus'])
    @cog_check()
    async def status_command(self,ctx:commands.Context):
        logger.info(f'{ctx.author.name} ({ctx.author.id}) ran status command')
        reference = ctx.message.reference
        message = ctx.message
        if reference and reference.message_id:
            chan_id = await self.bot.fetch_channel(reference.channel_id)
            message = await chan_id.fetch_message(reference.message_id)

        return await self.usenetbot.show_downloading_status(self.bot,ctx.channel.id, message)
    
    @commands.command()
    @cog_check()
    @sudo_check()
    async def resumeall(self,ctx):
        logger.info(f'{ctx.author.name} ({ctx.author.id}) ran resumeall command')
        res = await self.usenetbot.resumeall_task()
        if res:
            await ctx.send('Resumed all tasks successfully')
        else:
            await ctx.send('Unable to do what you asked. Please check logs')
    
    @commands.command()
    @cog_check()
    @sudo_check()
    async def pauseall(self,ctx):
        logger.info(f'{ctx.author.name} ({ctx.author.id}) ran pauseall command')
        res = await self.usenetbot.pauseall_task()
        if res:
            await ctx.send('Paused all tasks successfully')
        else:
            await ctx.send('Unable to do what you asked. Please check logs')
    
    @commands.command(aliases=['deleteall'])
    @cog_check()
    @sudo_check()
    async def cancelall(self,ctx):
        logger.info(f'{ctx.author.name} ({ctx.author.id}) ran cancelall command')
        res = await self.usenetbot.deleteall_task()
        if res:
            await ctx.send('Cancelled all tasks successfully')
        else:
            await ctx.send('Unable to do what you asked. Please check logs')


    @commands.command()
    @cog_check()
    async def pause(self,ctx:commands.Context,task_id:str=None):
        if not task_id:
            return await ctx.send(f'Please send the task id of the task you want to pause along with the command. `{ctx.prefix}pause SABnzbd_nzo_6w6458gv` . If the `_` convert the id to italics, no need to worry about it.')
        task_id = task_id.replace('\\','')
        if not ctx.author.id in SUDO_USERIDS:
            if ctx.author.id not in sabnzbd_userid_log:
                return await ctx.reply('No task found which you initiated....',mention_author=False)
            
            if task_id not in sabnzbd_userid_log[ctx.author.id]:
                return await ctx.reply('No task found which you initiated, with that task id.',mention_author=False)

        res = await self.usenetbot.pause_task(task_id=task_id)
        logger.info(f'{ctx.author.name} ({ctx.author.id}) ran pause command for {task_id} which resulted in {"success" if res else "failure"}')
        if res:
            await ctx.reply(f'Successfully paused task with task id : `{task_id}`',mention_author=False)
        else:
            await ctx.reply(f'No task found with task id : `{task_id}`',mention_author=False)


    @commands.command()
    @cog_check()
    async def resume(self,ctx:commands.Context,task_id:str=None):
        if not task_id:
            return await ctx.send(f'Please send the task id of the task you want to resume along with the command. `{ctx.prefix}resume SABnzbd_nzo_6w6458gv` . If the `_` convert the id to italics, no need to worry about it.')
        task_id = task_id.replace('\\','')
        if not ctx.author.id in SUDO_USERIDS:
            if ctx.author.id not in sabnzbd_userid_log:
                return await ctx.reply('No task found which you initiated....',mention_author=False)
            
            if task_id not in sabnzbd_userid_log[ctx.author.id]:
                return await ctx.reply('No task found which you initiated, with that task id.',mention_author=False)

        res = await self.usenetbot.resume_task(task_id=task_id)
        logger.info(f'{ctx.author.name} ({ctx.author.id}) ran resume command for {task_id} which resulted in {"success" if res else "failure"}')
        if res:
            await ctx.reply(f'Successfully resumed task with task id : `{task_id}`',mention_author=False)
        else:
            await ctx.reply(f'No task found with task id : `{task_id}`',mention_author=False)

    @commands.command(aliases=['cancel'])
    @cog_check()
    async def delete(self,ctx:commands.Context,task_id:str=None):
        if not task_id:
            return await ctx.send(f'Please send the task id of the task you want to cancel or delete along with the command. `{ctx.prefix}cancel SABnzbd_nzo_6w6458gv` . If the `_` convert the id to italics, no need to worry about it.')
        task_id = task_id.replace('\\','')
        if not ctx.author.id in SUDO_USERIDS:
            if ctx.author.id not in sabnzbd_userid_log:
                return await ctx.reply('No task found which you initiated....',mention_author=False)
            
            if task_id not in sabnzbd_userid_log[ctx.author.id]:
                return await ctx.reply('No task found which you initiated, with that task id.',mention_author=False)

        res = await self.usenetbot.delete_task(task_id=task_id)
        logger.info(f'{ctx.author.name} ({ctx.author.id}) ran delete command for {task_id} which resulted in {"success" if res else "failure"}')
        if res:
            await ctx.reply(f'Successfully cancelled task with task id : `{task_id}`',mention_author=False)
        else:
            await ctx.reply(f'No task found with task id : `{task_id}`',mention_author=False)

    @commands.command()
    @cog_check()
    async def nzbmirror(self,ctx:commands.Context):
        attachments = ctx.message.attachments
        if len(attachments) == 0:
            return await ctx.send('Please send one or multiple .nzb files along with this command.')
        
        any_one_added = False
        for nzb_file in attachments:
            if not nzb_file.filename.endswith('.nzb'):
                await ctx.send(f'`{nzb_file.filename}` is not a .nzb file')
                continue
            reply_msg = await ctx.reply('Adding nzb file please wait....',mention_author=False)
            await nzb_file.save(fp=f'nzbfiles/{nzb_file.filename}')

            res = await self.usenetbot.add_nzbfile(f'nzbfiles/{nzb_file.filename}')
            logger.info(f'{ctx.author.name} ({ctx.author.id}) added nzb file ({nzb_file.filename}) which resulted in {"success" if res["status"] else "failure"}')
            if res['status']:
                sabnzbd_userid_log.setdefault(ctx.author.id, []).append(res["nzo_ids"][0])
                any_one_added = True
                await reply_msg.edit(content=f"Your NZB file `{nzb_file.filename}` is successfuly Added in Queue.")
            else:
                reply_msg.edit(content=f"Something went wrong while processing your NZB file `{nzb_file.filename}`.")
        if any_one_added:
            asyncio.create_task(self.usenetbot.show_downloading_status(self.bot,ctx.channel.id, ctx.message))

    @commands.command(aliases=['nzbgrab','nzbadd','grab'])
    @cog_check()
    async def grabid(self,ctx:commands.Context,*,nzbids:str=None):
        if not nzbids:
            return await ctx.send(f'Please also send a nzb id to grab ... `{ctx.prefix}grab 5501963429970569893`\nYou can also send multiple ids in one go. Just partition them with a space.')
        nzbids = nzbids.strip()
        nzbhydra_idlist = nzbids.split(" ")
        if not nzbhydra_idlist:
            return await ctx.send("Please provide a proper ID.")
        replymsg = await ctx.send("Adding your requested ID(s). Please Wait...")
        success_taskids = []
        for id in nzbhydra_idlist:
            # Make sure that we are getting a number and not letters..
            if id.startswith("-"):
              if not id.split("-")[1].isnumeric():
                return await ctx.send("Please provide a proper ID.")
            elif not id.isnumeric():
              return await ctx.send("Please provide a proper ID.")
            
            nzburl = NZBHYDRA_URL_ENDPOINT.replace("replace_id", id)
            response = requests.get(nzburl)
            if "Content-Disposition" in response.headers:
                result2 = await self.usenetbot.add_nzburl(nzburl)
                logger.info(f'[GET] {ctx.author.name} ({ctx.author.id}) added nzb id ({id}) which resulted in {"success" if result2["status"] else "failure"} | {result2} | 2')   
                if result2["status"]:
                    success_taskids.append(result2["nzo_ids"][0])
            elif 'Retry-After' in response.headers:
                logger.info(f'{ctx.author.name} ({ctx.author.id}) added nzb id ({id}) which resulted in failure due getting Retry-After.')
                await ctx.send(f'Unable to add {id} , got a retry after message. Retry after {str(response.headers.get("Retry-After"))} seconds <t:{round(datetime.datetime.now().timestamp()+int(response.headers.get("Retry-After")))}:R>')
            else:
                await ctx.send(f'Some error has occured. \n Details: ```\n{remove_private_stuff(str(nzburl))}\n\n{remove_private_stuff(str(response.content))}\n\n{remove_private_stuff(str(response.headers))}```')

        if success_taskids:
            sabnzbd_userid_log.setdefault(ctx.author.id, []).extend(success_taskids)
            asyncio.create_task(self.usenetbot.show_downloading_status(self.bot,ctx.channel.id,ctx.message))

            await replymsg.delete()
            
            # This is to make sure the nzb's have been added to sabnzbd
            # TODO: Find a better way and more dynamic way to handle it.
            await asyncio.sleep(10) 
            file_names = await self.usenetbot.get_file_names(success_taskids)
            print(f'file_names={file_names}')
            
            formatted_file_names = "\n".join(["`" + s + "`" for s in file_names])
            print(f'formatted_file_names={formatted_file_names}')
            return await ctx.reply(f"Following files were added to queue:\n{formatted_file_names} ", mention_author=False)

        return await replymsg.edit(content="No task has been added.")

async def setup(bot):
    await bot.add_cog(Usenet(bot))
    print("Usenet cog is loaded")

discord.Color.green()