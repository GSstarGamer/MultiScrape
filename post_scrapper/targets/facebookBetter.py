from ..scrapper import Scrapper
from datetime import datetime
from pydantic import BaseModel, PositiveInt, NegativeInt
import re
from patchright.async_api import ElementHandle
from bs4 import BeautifulSoup

class FacebookBetter:
    def __init__(self, user: str, mentions: bool = True, recent: bool = False):

        self.Scrapper: Scrapper = None

        self.url = f'https://www.facebook.com/{user}'
        if mentions:
            self.url += '/mentions'
 
        self.recent = recent

        pass

    def __str__(self):
        return f"Facebook({self.url})"

    async def start(self, Scrapper: Scrapper):
        self.Scrapper = Scrapper
        self.page = Scrapper.page

        await Scrapper.open(self.url)

        while True:
            LikeButtons = await self.page.query_selector_all('div[aria-label="Like"]')

            for i, likeButton in enumerate(LikeButtons):
                outerButtons = await Scrapper.getParent(likeButton, 2)
                if len(await Scrapper.getChildren(outerButtons)) >= 3:
                    postDiv = await Scrapper.getParent(likeButton, 9)

                    print(await self._getPostBody(postDiv))
                

    async def _getPostBody(self, postDiv: ElementHandle):
        contentDiv = await self.Scrapper.traverseElement(postDiv, [2, 0, 0])
        return await self.Scrapper.getText(contentDiv)
    