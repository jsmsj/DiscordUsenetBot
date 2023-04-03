from dotenv import load_dotenv
import os
load_dotenv('config.env')

prefix = os.getenv('prefix')
bot_token = os.getenv('bot_token')

# SABnzbd Configs.
SAB_IP =os.getenv("SAB_IP")
SAB_PORT = os.getenv("SAB_PORT")
SAB_API_KEY = os.getenv("SAB_API_KEY")

# NZBHydra Configs.
HYDRA_URL = os.getenv("HYDRA_URL")
HYDRA_API_KEY = os.getenv("HYDRA_API_KEY")

AUTHORIZED_CHANNELS = os.getenv("AUTHORIZED_CHANNELS")
AUTHORIZED_CHANNELS_LIST = [int(channel_id) for channel_id in AUTHORIZED_CHANNELS.replace('[', '').replace(']', '').split(",")]
SUDO_USERID = os.getenv("SUDO_USERID")