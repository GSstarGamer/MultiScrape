from ..scrapper import Scrapper
from bs4 import BeautifulSoup, Tag
import time
from datetime import datetime
from pydantic import BaseModel, PositiveInt, NegativeInt
import re
import asyncio
import json
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

class Facebook:
    def __init__(self, user: str, mentions: bool = True, recent: bool = False):

        self.Scrapper: Scrapper = None

        self.url = f'https://www.facebook.com/{user}'
        if mentions:
            self.url += '/mentions'

        self.recent = recent

        self.posts: list[Post] = []

        pass

    def __str__(self):
        return f"Facebook({self.url})"

    async def start(self, Scrapper: Scrapper):
        self.Scrapper = Scrapper
        self.page = Scrapper.page

        
        def extract_pfbids_from_response(json_data):
            text = json.dumps(json_data)
            return re.findall(r'pfbid[A-Za-z0-9]+', text)

        await Scrapper.open(self.url)

        # # Hook GraphQL responses with "pfbid" inside
        # async def handle_response(response):
        #     if '/api/graphql/' in response.url and response.request.method == 'POST':
        #         try:
        #             json_data = await response.json()
        #             pfbids = extract_pfbids_from_response(json_data)
        #             if pfbids:
        #                 print(f"🔗 Found pfbid(s): {pfbids}")
        #         except Exception as e:
        #             pass  # ignore parsing errors

        # self.page.on("response", handle_response)

        # await intercept_graphql(self.page)


        
        await self.page.locator("div[aria-label='Sort']").click()

        sortbySelector = "div[aria-label='Sort by']"
        sortby = await self.page.wait_for_selector(sortbySelector)
        soup = await Scrapper.soup()
        sortby = soup.select_one(sortbySelector)
        mostRecent = await Scrapper.convertTag(self._transverseTag(sortby, [2, 0, 1]))
        await mostRecent.click()

        apply = await Scrapper.convertTag(self._transverseTag(sortby, [3, 0, 1]))
        await apply.click()



        self.page.set_default_timeout(5000)

        await self.page.wait_for_selector('div[aria-label="Like"]')
        while True:
            soup = await Scrapper.soup()

            like_divs = soup.select('div[aria-label="Like"]')

            for like_div in like_divs:

                if len(like_div.parent.parent.find_all(recursive=False)) >= 3:
                    postDiv = like_div.parent.parent.parent.parent.parent.parent.parent.parent.parent
                    
                    content = await self._getPostBody(postDiv)
                    if content is None:
                        content = ""
                    profileName = await Scrapper.attribSearch(postDiv, "data-ad-rendering-role", "profile_name")
                    if profileName is None:
                        await Scrapper.scroll(0, 500, duration=0.1, steps=30)
                        break

                    profileName = profileName.getText(strip=True)

                    if not any(post.content == content and post.username == profileName for post in self.posts):
                        await Scrapper.scrollTo(self._transverseTag(postDiv, [1]), 0, 1)
                        # get time tag
                        try:
                            # Extract and convert the time tag from the post
                            timeTag = await self._getTimeTag(postDiv)
                            timeLocator = await Scrapper.convertTag(timeTag)
                            await timeLocator.scroll_into_view_if_needed()

                            # Scroll to and hover the time element
                            # await Scrapper.scrollTo(timeTag, duration=0.0, steps=10)

                            closeOption = self.page.locator("div[aria-label='Close']")

                            try:
                                if await closeOption.is_visible():
                                    await closeOption.click(timeout=500)
                                await timeLocator.hover(force=True)
                            except:
                                pass

                            # Wait for the target selector to appear (pure __fb-dark-mode class only)
                            selector = 'div.__fb-dark-mode[class="__fb-dark-mode"]'
                            await self.page.wait_for_selector(selector, state="attached")

                            # Parse page content and extract timestamp
                            soup = await Scrapper.soup()
                            timeText = soup.select_one(selector).get_text(strip=True)
                            epoch = self._toEpoch(timeText)

                            # Update tag and extract profile info
                            updatedTag = await self.Scrapper.updateTag(timeTag)
                            url = await self._getURL(updatedTag)




                        except Exception as e:
                            print(f"[ERROR] Failed to get post: {e}")
                            await Scrapper.scroll(0, 500, duration=0.1, steps=30)
                            break


                        

                        print('-' * 20)

                        print("profile name:", profileName)
                        print("post URL:", url)


                        print(f"time: {timeText}. epoch:", epoch)

                        reactionsCount = await self._getReactions(postDiv)

                        print(f"reactions: {reactionsCount}")

                        print(content)

                        postClass = Post(
                            post_url=url,
                            epoch=epoch,
                            username=profileName,
                            content=content,
                            reactions=reactionsCount,
                            comments=0,
                            )
                        
                        self.posts.append(postClass)

                        postDiv = await self.Scrapper.convertTag(postDiv)
                        # await postDiv.evaluate("el => el.parentElement.parentElement.style.display = 'none'")
                        # await postDiv.evaluate("el => el.parentElement.parentElement.remove()")

                        print('-' * 20)
                        break



            # await Scrapper.scroll(0, 500, duration=0.1, steps=30)
            
    def _transverseTag(self, root, path) -> Tag:
        from bs4.element import Tag
        current = root
        for depth, idx in enumerate(path):
            if not isinstance(current, Tag):
                return None
            children = [c for c in current.children if isinstance(c, Tag)]
            if idx >= len(children):
                return None
            current = children[idx]
        return current


    def _toEpoch(self, dateString: str):
        try:
            dt = datetime.strptime(dateString, "%A %d %B %Y at %H:%M")
            return int(dt.timestamp())
        except:
            return 0

    async def _getURL(self, timeTag: Tag):
        timeTag = self._transverseTag(timeTag, [0])
        url = timeTag.get("href", "")
        
        if url != '':
            parsed = urlparse(url)
            query = parse_qs(parsed.query)

            # Filter out unwanted keys (e.g., keys that start with "__cft__" or "__tn__")
            filtered_query = {
                k: v for k, v in query.items()
                if not (k.startswith("__cft__") or k.startswith("__tn__"))
            }

            clean_query = urlencode(filtered_query, doseq=True)
            url = urlunparse(parsed._replace(query=clean_query))

        return url

    

        # if href.startswith("/"):
        #     href = "https://www.facebook.com" + href
        # elif href.startswith("?"):
        #     href = "https://www.facebook.com/" + href

        # # Match known formats
        # post_match = re.search(r"facebook\.com/([^/?#]+)/(?:(posts|videos))/([^/?#]+)", href)
        # profile_match = re.search(r"facebook\.com/profile\.php\?id=([0-9]+)", href)
        # permalink_match = re.search(r"facebook\.com/permalink\.php\?story_fbid=([0-9]+)&id=([0-9]+)", href)

        # if post_match:
        #     user_id, content_type, content_id = post_match.groups()
        #     url = f"https://www.facebook.com/{user_id}/{content_type}/{content_id}"
        #     return user_id, content_type, content_id, url

        # if profile_match:
        #     user_id = profile_match.group(1)
        #     url = f"https://www.facebook.com/profile.php?id={user_id}"
        #     return user_id, "profile", "", url

        # if permalink_match:
        #     content_id, user_id = permalink_match.groups()
        #     url = f"https://www.facebook.com/permalink.php?story_fbid={content_id}&id={user_id}"
        #     return user_id, "permalink", content_id, url

        # return "", "", "", ""



    async def _getTimeTag(self, postDiv: Tag) -> Tag | None:
        return self._transverseTag(postDiv, [1, 0, 1, 0, 1, 0, 0, 0, 0])
    

    async def _getPostBody(self, postDiv):
        # for child in postDiv.find_all(recursive=False):
        #     target = self._transverseTag(child, [0, 0])
        #     if target.get("data-ad-rendering-role") == "story_message":
        #         return target.get_text(strip=True)

        # return ""
        textTag = self._transverseTag(postDiv, [2, 0, 0])
        return textTag.getText() or ""


    async def _getReactions(self, postDiv):
        # use your now-corrected index list here
        details = self._transverseTag(postDiv, [3, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1])
        if details is None:
            return 0
        return int(details.get_text(strip=True))
        # print(reactions)

        # comments, shares = 0, 0

        # if details.get

            # commentsTag  = self._transverseTag(details, [/* path to comments count  */])


        # comments  = int(commentsTag.get_text(strip=True).split(" ",1)[0]) or 0
        # shares    = int(sharesTag.get_text(strip=True).split(" ",1)[0]) or 0

        # return reactions, comments, shares



class Post(BaseModel):
    post_url: str
    epoch: int
    username: str
    content: str
    reactions: int | None
    comments: int | None
