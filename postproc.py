#!/usr/bin/python3

from logging.handlers import RotatingFileHandler
import subprocess
import logging
import requests
import shutil
import sys
import os
import re
import base64
import datetime


DISCORD_NOTIFICATION_WEBHOOK_URL = ""
SHOW_DRIVE_LINK = False

def b64e(s):
    return base64.urlsafe_b64encode(s.encode()).decode()

def encode_link(link,author):
    # https://links.gamesdrive.net/#/link/{base64}.{uploaderB64}
    e_link = b64e(link)
    e_author = b64e(author)
    return f"https://links.gamesdrive.net/#/link/{e_link}.{e_author}"

# Takes all the parameters given by sabnzbd such as filename,  filepath etc.
try:
    (
        scriptname,
        directory,
        orgnzbname,
        jobname,
        reportnumber,
        category,
        group,
        postprocstatus,
        url,
    ) = sys.argv
except:
    print("No commandline parameters found.")
    sys.exit(1)


# ==================================================================================


# log file path of sabnzbd log.
LOGFILE_PATH = "/home/master/.config/sabnzbd/logs/sabnzbd.log"

#Rclone upload directory and flags.  
RCLONE_REMOTE_NAME = ""
RCLONE_DIRECTORY_NAME = "UsenetUpload"  # leave empty if there isn't one.
RCLONE_UPLOAD_DIRECTORY = directory.split("/")[-1]
DRIVE_UPLOAD_DIRECTORY = f"{RCLONE_REMOTE_NAME}:{RCLONE_DIRECTORY_NAME}/{RCLONE_UPLOAD_DIRECTORY}"

rclone_command = f"gclone copy -v --stats=1s --stats-one-line --drive-chunk-size=256M --fast-list --transfers=1 --exclude _UNPACK_*/** --exclude _FAILED_*/** --exclude *.rar '{directory}' '{DRIVE_UPLOAD_DIRECTORY}' "


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        RotatingFileHandler(LOGFILE_PATH, mode="w+", maxBytes=5000000, backupCount=10),
        logging.StreamHandler()])


def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)


def get_readable_bytes(size: str) -> str:
    dict_power_n = {0: "", 1: "Ki", 2: "Mi", 3: "Gi", 4: "Ti"}

    if not size:
        return ""
    power = 2 ** 10
    raised_to_pow = 0

    while size > power:
        size /= power
        raised_to_pow += 1
    return f"{str(round(size, 2))} {dict_power_n[raised_to_pow]}B"

def convert_bytes_to_size(bytes: str) -> str:
    """
    Convert bytes (given as a string) to human-readable size in KB, MB, GB, or TB.
    """
    sizes = ["B", "KB", "MB", "GB", "TB"]
    if not bytes.isdigit():
        raise ValueError("Input must be a positive integer")
    bytes = int(bytes)
    if bytes == 0:
        return "0 B"
    idx = min(4, int(math.log(bytes, 1024)))
    size = bytes / (1024 ** idx)
    return f"{size:.2f} {sizes[idx]}"


def webhook_notification(message:str):
    data = {
        "content": message,
        "embeds": None,
        "attachments": [],
	"username": "FlightClubUsenetBot",
    	"avatar_url": "https://i.imgur.com/ly52aG7.png"
    }
    headers = {
        'Content-Type': 'application/json'
    }
    
    response:requests.Response = requests.post(DISCORD_NOTIFICATION_WEBHOOK_URL,headers=headers,json=data)

    if response.status_code == 204:
        sys.exit(0)

    print("Something happened.....")
    sys.exit(1)

def webhook_notification_embed(message:str,**kwargs):
    if kwargs.get('primitive'):
        data = {
            "content": message,
            "embeds": None,
            "attachments": []
        }
    else:
        now = datetime.datetime.now(datetime.timezone.utc)
        time_str = now.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        data = {
    "content": None,
    "embeds": [
        {
        "title": "New Upload !!!",
        "description": f"**{kwargs.get('filename')}** has been uploaded to drive.",
        "color": 3066993,
        "fields": [  
            {
            "name": "Size",
            "value": f"**{kwargs.get('file_size')}**"
            },
            {
            "name": "Location",
            "value": "**[FlightClub Contrib] / UsenetUpload /**"
            }
        ],
        "timestamp": f"{time_str}"
        }
    ],
    "username": "FlightClubUsenetBot",
    "avatar_url": "https://i.imgur.com/ly52aG7.png",
    "attachments": []
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    response:requests.Response = requests.post(DISCORD_NOTIFICATION_WEBHOOK_URL,headers=headers,json=data)

    if response.status_code == 204:
        sys.exit(0)
    else:
        if not kwargs.get('primitive'):
            data.pop("timestamp")
            response:requests.Response = requests.post(DISCORD_NOTIFICATION_WEBHOOK_URL,headers=headers,json=data)
            if response.status_code == 204:
                sys.exit(0)


    print("Something happened.....")
    sys.exit(1)


def run_command(command):
    with subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True
    ) as proc:

        while True:
            output = proc.stdout.readline().decode("UTF-8").strip()

            if output != "":
                if ":" in output:
                    output = output.split(":")[-1].strip()
                LOGGER(__name__).info(f"Uploading to drive: {output}")

            if output == "" and proc.poll() is not None:
                LOGGER(__name__).info("File has been successfully uploaded to gdrive.")
                break


if re.search(r"(http|https)", jobname):
    jobname = "N/A"


reasons = {
    "1": "Failed verification",
    "2": "Failed unpack",
    "3": "Failed unpack / verification",
}


if str(postprocstatus) in reasons:
    reason = reasons[postprocstatus]
    notification_message = f"`🗂 {jobname}`\n\n{reason} "
    webhook_notification(message=notification_message,primitive=True)
    sys.exit(1)


run_command(rclone_command)

# deleting file from local drive.
shutil.rmtree(directory)
try:
    file_size = os.environ["SAB_BYTES_DOWNLOADED"]
    file_size = get_readable_bytes(int(file_size))
except:
    file_size = "N/A"


drive_link = ""
if SHOW_DRIVE_LINK:
    drive_link = subprocess.check_output(
        ["rclone", "link", f"{DRIVE_UPLOAD_DIRECTORY}"]).decode("utf-8")

    if "drive.google.com" not in drive_link:
        drive_link = "Something went wrong!"

    print(drive_link)
    drive_link = f'[Drive Link]({encode_link(drive_link,"SecretBot")})'


notification_message = (
    f"`📁 {jobname}`\n\n{file_size} | Success |{drive_link}")

# webhook_notification(message=None, filename=jobname,file_size=file_size)
webhook_notification(message=notification_message)
