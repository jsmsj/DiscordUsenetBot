import json
import html
import httpx
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from loggerfile import logger

from cogs._helpers import humanbytes,NZBHYDRA_ENDPOINT, NZBHYDRA_STATS_ENDPOINT,format_time_since


class NzbHydra:
    def __init__(self):
        self.NZBHYDRA_ENDPOINT = NZBHYDRA_ENDPOINT
        self.NZBHYDRA_STATS_ENDPOINT = NZBHYDRA_STATS_ENDPOINT
        self.client = httpx.AsyncClient(timeout=30)

    def parse_xml(self, response, query):
        root = ET.fromstring(response)

        channel = root.find("channel")
        search_result = [
            [
                item.find("title").text,
                humanbytes(int(item.find("size").text))
                if item.find("size") is not None
                else "",
                item.find("guid").text,
                item.find("pubDate").text,
            ]
            for item in channel.findall("item")
        ]

        title = f"<h4> NZB Search Results for: {query}</h4>\n"
        message = ""
        if len(search_result) == 0:
            logger.info(f'Searched for {query} found 0 results....')
            return None
        for index, result in enumerate(search_result):
            message += f"<strong>{result[0]}</strong> "
            message += f"[{result[1]}]\n"

            # Show how old the nzb was on indexer
            dt = datetime.strptime(result[3], '%a, %d %b %Y %H:%M:%S %z')
            time_str = format_time_since(dt)
            
            ID = result[2]

            # if "-" in ID:
            #     ID = ID.replace("-", "")
            message += f"<code>COPY Me: {ID} Age: {time_str}</code>\n"
            if index == 100:
                break

        if message:
            html_content = title + message
            return (html_content, index + 1)
        return None

    async def query_search(self, query):
        response = await self.client.get(
            self.NZBHYDRA_ENDPOINT, params={"t": "search", "q": query})
        logger.info(f'Searching (nzb_id) for {query}')
        return self.parse_xml(response.text, query)

    async def movie_search(self, query):
        response = await self.client.get(
            self.NZBHYDRA_ENDPOINT, params={"t": "movie", "q": query})
        logger.info(f'Searching (movie) for {query}')
        return self.parse_xml(response.text, query)

    async def series_search(self, query):
        response = await self.client.get(
            self.NZBHYDRA_ENDPOINT, params={"t": "tvsearch", "q": query})
        logger.info(f'Searching (series) for {query}')
        return self.parse_xml(response.text, query)

    async def imdb_movie_search(self, imdbid):
        response = await self.client.get(
            self.NZBHYDRA_ENDPOINT, params={"t": "movie", "imdbid": imdbid})
        logger.info(f'Searching (imdb movie) for {imdbid}')
        return self.parse_xml(response.text, imdbid)

    async def imdb_series_search(self, imdbid):
        response = await self.client.get(
            self.NZBHYDRA_ENDPOINT, params={"t": "tvsearch", "imdbid": imdbid})
        logger.info(f'Searching (imdb series) for {imdbid}')
        
        return self.parse_xml(response.text, imdbid)

    async def list_indexers(self):
        response = await self.client.get(self.NZBHYDRA_STATS_ENDPOINT)
        indexersDetail = response.json()["indexerApiAccessStats"]
        indexers_list = [
            indexersDetail[x]["indexerName"] for x in range(len(indexersDetail))]
        if not indexers_list:
            return None

        message = "List Of Indexers -\n\n```\n"
        for i,indexer in enumerate(indexers_list):
            message += f"{i+1}. {indexer}\n"
        message+='\n```'
        return message

