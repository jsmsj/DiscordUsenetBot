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
HYDRA_IP = os.getenv("HYDRA_IP")
HYDRA_PORT = os.getenv("HYDRA_PORT")
HYDRA_API_KEY = os.getenv("HYDRA_API_KEY")

