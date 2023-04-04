FROM python:3.10
WORKDIR /discordusenetbot
COPY requirements.txt /discordusenetbot/
RUN pip install -r requirements.txt
COPY . /discordusenetbot
CMD python main.py