"""Imports"""
import discord
from discord.ext import commands
from main import logger,BotStartTime,scheduler
from cogs._helpers import SABNZBD_ENDPOINT,humantime,humanbytes
import httpx
import psutil
import time
import datetime
import re
import aiofiles
from cogs._config import *


downloading_status_msgids = {} 


class UsenetHelper:
    def __init__(self) -> None:
        self.SABNZBD_API = f"{SABNZBD_ENDPOINT}&output=json"
        self.client = httpx.AsyncClient(timeout=10)
        self.__number_of_blocks = 11

        # progress bar ascii animation
        self.__remaining_block_ascii = "▱"
        self.__completed_block_ascii = "▰"


    def footer_message(self):
        # calculating system speed per seconds.
        net_io_counters = psutil.net_io_counters()
        bytes_sent = net_io_counters.bytes_sent
        bytes_recv = net_io_counters.bytes_recv

        time.sleep(1)

        net_io_counters = psutil.net_io_counters()
        download_speed = net_io_counters.bytes_recv - bytes_recv
        upload_speed = net_io_counters.bytes_sent - bytes_sent

        botuptime = humantime((datetime.datetime.utcnow()-BotStartTime).total_seconds())
        msg = f"🟢 DL: {humanbytes(download_speed)}/s 🟡 UL: {humanbytes(upload_speed)}/s | ⌚ Uptime: {botuptime}"
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
            # status_page += "**Downloading -\n\n**"
            status_embed.description = '**Downloading -**\n\n'

            for index, queue in enumerate(downloading_queue_list):
                filled_blocks = round(
                    int(queue["percentage"]) * self.__number_of_blocks / 100)
                
                unfilled_blocks = self.__number_of_blocks - filled_blocks

                file_name = queue["filename"]
                if re.search(r"(http|https)", file_name):
                    file_name = "Adding file from ID."
                status_embed.description += f'**🗂 FileName:** `{file_name}`\n\n{self.show_progress_still(int(queue["percentage"]))} {queue["percentage"]}%\n\n' \
                                            f"**{queue['sizeleft']}** remaining of **{queue['size']}**\n" \
                                            f"**Status:** {queue['status']} | **ETA:** {queue['timeleft']}\n" \
                                            f"**Task ID:** `{queue['nzo_id']}`\n━━━━━━━━━━━━━━━━━━━━\n"
                # status_page += f"**🗂 FileName:** {file_name}\n"
                # status_page += f"**{queue['percentage']}%**  `[{self.__completed_block_ascii * filled_blocks}{self.__remaining_block_ascii * unfilled_blocks}]`\n"
                # status_page += (
                #     f"**{queue['sizeleft']}** remaining of **{queue['size']}**\n")
                
                # status_page += (
                #     f"**Status:** {queue['status']} | **ETA:** {queue['timeleft']}\n")
                
                # status_page += f"**Task ID:** `{queue['nzo_id']}`\n\n"

                if index == 4 and len(downloading_queue_list) > 4:
                    # status_page += f"**+ {max(len(downloading_queue_list)-4, 0)} Ongoing Task...**\n\n"
                    status_embed.description += f"**+ {max(len(downloading_queue_list)-4, 0)} Ongoing Tasks...**\n\n"
                    break



        if postprocessing_queue_list:
            # if status_page:
            #     status_page += "━━━━━━━━━━━━━━━━━━━━\n"
            if status_embed.description not in ['',None]:
                status_embed.description += '━━━━━━━━━━━━━━━━━━━━\n'

            # status_page += "**Post Processing -**\n\n"
            status_embed.description += "**Post Processing -\n\n**"
            for index, history in enumerate(postprocessing_queue_list):

                file_name = history["name"]
                if re.search(r"(http|https)", file_name):
                    file_name = "N/A"

                # status_page += f"**🗂 FileName :** {file_name}\n"
                # status_page += f"**Status :** {history['status']}\n"
                
                status_embed.description += f"**🗂 FileName :** {file_name}\n" \
                                            f"**Status :** {history['status']}\n"

                action = history.get("action_line")
                if isinstance(action, list):
                    # status_page += f"**Action :** {action[0]}\n"
                    status_embed.description += f"**Action :** {action[0]}\n"

                if action and "Running script:" in action:
                    action = action.replace("Running script:", "")
                    # status_page += f"**Action :** {action.strip()}\n"

                    status_embed.description += f"**Action :** {action.strip()}\n"

                if index == 4 and len(postprocessing_queue_list) > 4:
                    # status_page += f"\n**+ Extra Queued Task...**\n\n"
                    status_embed.description+= f"\n**+ Extra Queued Task...**\n\n"
                    break
                
                # status_page += "\n"

        # if status_page:
        #     status_page += "━━━━━━━━━━━━━━━━━━━━\n"
        #     status_page += self.footer_message()

        if status_embed.description not in ['',None]:
            status_embed.set_footer(text=self.footer_message())


        return '',status_embed
    
    async def check_task(self, task_id):
        response = await self.client.get(
            self.SABNZBD_API, params={"mode": "queue", "nzo_ids": task_id})
        
        response = response.json()
        return bool(response["queue"]["slots"])

    async def get_task(self, task_id):
        response = await self.client.get(
            self.SABNZBD_API, params={"mode": "queue", "nzo_ids": task_id})
        
        response = response.json()
        return bool(response["queue"]["slots"])

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
            excess+=f'\n[Latest Message]({kwargs.get("jump_url")})'
        
        em = discord.Embed(title='📊 Status',color=discord.Color.green())
        em.description = f'See the latest message for status....{excess}'
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
                print(e)
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
        reference = ctx.message.reference
        message = ctx.message
        # if not reference:
        #     # return await ctx.send('incorrect usage') #TODO better explain
        #     message= None
        # if reference.message_id is None:
        #     message = None
        if reference and reference.message_id:
            chan_id = await self.bot.fetch_channel(reference.channel_id)
            message = await chan_id.fetch_message(reference.message_id)

        return await self.usenetbot.show_downloading_status(self.bot,ctx.channel.id, message)
    

        


async def setup(bot):
    await bot.add_cog(Usenet(bot))
    print("Usenet cog is loaded")