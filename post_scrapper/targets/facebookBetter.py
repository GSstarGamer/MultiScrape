from ..scrapper import Scrapper
from datetime import datetime
from pydantic import BaseModel, PositiveInt, NegativeInt
import re
from patchright.async_api import ElementHandle
from bs4 import BeautifulSoup
import asyncio
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


class FacebookBetter:
    def __init__(self, user: str, mentions: bool = True, recent: bool = False):

        self.Scrapper: Scrapper = None

        self.url = f'https://www.facebook.com/{user}'
        if mentions:
            self.url += '/mentions'

        self.mentions = mentions
        self.recent = recent
        
        self.posts: list[Post] = []
        self.postsID = set()
        pass

    def __str__(self):
        return f"Facebook({self.url})"

    async def start(self, Scrapper: Scrapper):
        self.Scrapper = Scrapper
        self.page = Scrapper.page

        await Scrapper.open(self.url)

        if self.recent and self.mentions:
            await self._setLatest()

        self.page.set_default_timeout(5000)

        while True:
            await self.page.wait_for_selector('div[aria-label="Like"]', state='attached')
            LikeButtons = await self.page.query_selector_all('div[aria-label="Like"]')

            for i, likeButton in enumerate(LikeButtons):
                outerButtons = await Scrapper.getParent(likeButton, 2)
                if len(await Scrapper.getChildren(outerButtons)) >= 3:
                    postDiv = await Scrapper.getParent(likeButton, 9)
                    
                    possibleReelTag = await self.Scrapper.traverseElement(postDiv, [1])
                    if await self.Scrapper.getAttr(possibleReelTag, 'aria-label') == 'Open reel in Reels Viewer': # aria-label="Open reel in Reels Viewer"
                        continue

                    UniqueID = await self.getUniqueID(postDiv)

                    await self._checkSeeMore(postDiv)

                    if UniqueID not in self.postsID:
                        try:
                            print('-' * 20)
                            self.postsID.add(UniqueID)
                            profileName = await self._getProfileName(postDiv)
                            print(profileName)
                            postContent = await self._getPostBody(postDiv)
                            postContent = postContent.replace('\n', ' ')
                            print(postContent)
                            
                            timeTag = await self._getTimeTag(postDiv)
                            await Scrapper.scrollTo(timeTag, 0.05, 30)
                            time = await self._getTime(timeTag)
                            print("Time:", time)
                            url = await self._getURL(timeTag)
                            print("URL:", url)
                            reactions = await self._getReactions(postDiv)
                            print("Reactions:", reactions)
                        except Exception as e:
                            Scrapper.log.warning("Failed to get post details", exc_info=e)
                            await Scrapper.scroll(0, 500, duration=0.1, steps=30)
                            break    

                        postClass = Post(
                            post_url=url,
                            epoch=time,
                            username=profileName,
                            content=postContent,
                            reactions=reactions,
                            comments=0,
                            )

                        self.posts.append(postClass)
                        print('-' * 20)
                        break
            
            await Scrapper.scroll(0, 1000, duration=0.1, steps=30)

    async def _checkSeeMore(self, postDiv: ElementHandle) -> None:
        button_locator = await postDiv.query_selector('[role="button"]:has-text("See more")')
        if button_locator and await button_locator.is_visible():
            await button_locator.click()


    async def _setLatest(self):
        await self.page.locator("div[aria-label='Sort']").click()

        sortby = await self.page.wait_for_selector("div[aria-label='Sort by']")
        mostRecent = await self.Scrapper.traverseElement(sortby, [2, 0, 1])
        await mostRecent.click()

        apply = await self.Scrapper.traverseElement(sortby, [3, 0, 1])
        await apply.click()

    async def getUniqueID(self, postDiv: ElementHandle) -> str:
        profileNameTag = await self.Scrapper.attribSearch(postDiv, "data-ad-rendering-role", "profile_name")

        profileURLTag =await profileNameTag.query_selector("a[href]")

        return await self.Scrapper.getAttr(profileURLTag, "href")

    async def _getPostBody(self, postDiv: ElementHandle) -> str:
        contentDiv = await self.Scrapper.attribSearch(postDiv, "data-ad-rendering-role", "story_message") # data-ad-rendering-role="story_message"
        return await self.Scrapper.getText(contentDiv)


    async def _getProfileName(self, postDiv: ElementHandle) -> str:
        contentDiv = await self.Scrapper.attribSearch(postDiv, "data-ad-rendering-role", "profile_name") # data-ad-rendering-role="profile_name"
        return await self.Scrapper.getText(contentDiv)
    
    async def _getTimeTag(self, postDiv: ElementHandle) -> ElementHandle | None:
        return await self.Scrapper.traverseElement(postDiv, [1, 0, 1, 0, 1, 0, 0, 0, 0])

    def _toEpoch(self, dateString: str):
        try:
            dt = datetime.strptime(dateString, "%A %d %B %Y at %H:%M")
            return int(dt.timestamp())
        except:
            return 0
    
    def _strip(self, str: str) -> str:
        return str.replace(" ", "").replace("\n", "").replace(" ", "").replace("Verified account", "")

    async def _getTime(self, timeTag: ElementHandle) -> int:
        mouse = self.page.mouse

        box = await timeTag.bounding_box()  

        
        target_x = box["x"] + box["width"] / 2
        target_y = box["y"] + box["height"] / 2

        while True:
            newTimeBox = await self.page.query_selector('div.__fb-dark-mode[class="__fb-dark-mode"]')
            if newTimeBox:
                break

            # await asyncio.sleep(0.1)
            if not await timeTag.is_visible():
                await timeTag.scroll_into_view_if_needed(timeout=1000)
    
            await mouse.move(target_x, target_y)
        
        time = self._toEpoch(await self.Scrapper.getText(newTimeBox))
        await mouse.move(0, 0)
        return time

    def parseURL(self, url: str) -> str:
            parsed = urlparse(url)
            query = parse_qs(parsed.query)

            filtered_query = {
                k: v for k, v in query.items()
                if not (k.startswith("__cft__") or k.startswith("__tn__"))
            }

            clean_query = urlencode(filtered_query, doseq=True)
            return urlunparse(parsed._replace(query=clean_query))
    
    async def _getURL(self, timeTag: ElementHandle):
        timeTag = await self.Scrapper.traverseElement(timeTag, [0])
        url = await self.Scrapper.getAttr(timeTag, "href")
        if url != '':
            url = self.parseURL(url)

        
        return url
    
    def convert_shorthand_number(self, value) -> int:
        if value is None:
            return 0

        if isinstance(value, (int, float)):
            return int(value)

        if isinstance(value, str):
            s = value.strip().upper().replace(",", "")
            if not s:
                return 0

            try:
                if s.endswith("K"):
                    return int(float(s[:-1]) * 1_000)
                elif s.endswith("M"):
                    return int(float(s[:-1]) * 1_000_000)
                elif s.endswith("B"):
                    return int(float(s[:-1]) * 1_000_000_000)
                else:
                    return int(float(s))
            except ValueError:
                pass

        return 0

    async def _getReactions(self, postDiv: ElementHandle) -> int:
        details = await self.Scrapper.traverseElement(postDiv, [3, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1])
        if not details:
            return 0
        return self.convert_shorthand_number(await self.Scrapper.getText(details))

class Post(BaseModel):
    post_url: str
    epoch: int
    username: str
    content: str
    reactions: int | None
    comments: int | None
