
import discord
from datetime import datetime,timedelta
from cogs._config import *
import requests
from telegraph.aio import Telegraph
import sys
from httpx import AsyncClient


def embed(title,description): #,url=None
    em = discord.Embed(title=title,description=description,color=discord.Color.green(),timestamp=datetime.now())
    # em.set_footer(text="")
    # if url:
    #     btn = Button(label="Link",url=url)
    #     view = View()
    #     view.add_item(btn)
    #     return [em,view]
    return [em,None]


SABNZBD_ENDPOINT = f"http://{SAB_IP}:{SAB_PORT}/sabnzbd/api?apikey={SAB_API_KEY}"
NZBHYDRA_ENDPOINT = f"{HYDRA_URL}/api?apikey={HYDRA_API_KEY}"

NZBHYDRA_URL_ENDPOINT = f"{HYDRA_URL}/getnzb/api/replace_id?apikey={HYDRA_API_KEY}"
NZBHYDRA_STATS_ENDPOINT = f"{HYDRA_URL}/api/stats?apikey={HYDRA_API_KEY}"

def check_before_starting(service):
    if service.lower() == 'sabnzbd':
        response = requests.get(SABNZBD_ENDPOINT, timeout=3)
        response.raise_for_status()
    elif service.lower() == 'nzbhydra':
        response = requests.get(NZBHYDRA_ENDPOINT, timeout=10)
        response.raise_for_status()
        if "Wrong api key" in response.text:
            raise ValueError("Wrong API value in configs.")

def humanbytes(size: int) -> str:
    if not size:
        return ""
    power = 2 ** 10
    number = 0
    dict_power_n = {
        0: " ",
        1: "K",
        2: "M",
        3: "G",
        4: "T",
        5: "P"
    }
    while size > power:
        size /= power
        number += 1
    return str(round(size, 3)) + " " + dict_power_n[number] + 'B'


async def katbin_paste(text: str) -> str:
    """
    paste the text in katb.in website.
    """

    katbin_url = "https://katb.in/api/paste"
    client = AsyncClient()
    try:
        paste_post = await client.post(
            katbin_url,
            json={"paste": {"content": f"{text}"}})
        
        paste_post = paste_post.json()
        
        output_url = "https://katb.in/{}".format(paste_post["id"])
        
        await client.aclose()
        return output_url
    except:
        return "something went wrong while pasting text in katb.in."

async def telegraph_paste(content: str, title="Discord Usenet Bot") -> str:
    """
    paste the text in telegra.ph (graph.org) website (text should follow proper html tags).
    """

    telegraph = Telegraph(domain="graph.org")

    await telegraph.create_account(short_name=title)
    html_content = content.replace("\n", "<br>")
    try:
        response = await telegraph.create_page(
            title="Discord Usenet Bot search result -", html_content=html_content)
        response = response["url"]
    except:
        response = await katbin_paste(content)

    try:
        await telegraph.revoke_access_token()
    except: pass
    return response

def humantime(seconds):
    time_str = str(timedelta(seconds=seconds))
    return time_str.split('.')[0]