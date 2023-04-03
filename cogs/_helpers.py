from discord.ui import Button,View
import discord
from datetime import datetime
from cogs._config import *
import requests
import sys


def embed(title,description,url=None):
    em = discord.Embed(title=title,description=description,color=discord.Color.green(),url="https://github.com/jsmsj/gdriveclonebot",timestamp=datetime.now())
    # em.set_footer(text="")
    if url:
        btn = Button(label="Link",url=url)
        view = View()
        view.add_item(btn)
        return [em,view]
    return [em,None]


SABNZBD_ENDPOINT = f"http://{SAB_IP}:{SAB_PORT}/sabnzbd/api?apikey={SAB_API_KEY}"
NZBHYDRA_ENDPOINT = f"http://{HYDRA_IP}:{HYDRA_PORT}/api?apikey={HYDRA_API_KEY}"

NZBHYDRA_URL_ENDPOINT = f"http://{HYDRA_IP}:{HYDRA_PORT}/getnzb/api/replace_id?apikey={HYDRA_API_KEY}"
NZBHYDRA_STATS_ENDPOINT = f"http://{HYDRA_IP}:{HYDRA_PORT}/api/stats?apikey={HYDRA_API_KEY}"

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