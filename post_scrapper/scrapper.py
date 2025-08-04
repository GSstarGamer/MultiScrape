import os
import logging
import asyncio
from patchright.async_api import async_playwright, Browser, BrowserContext, Page, Locator
import random
import math
from typing import Literal
from bs4 import BeautifulSoup, PageElement, Tag
import lxml.etree as etree

log = logging.getLogger("Scrapper")
formatter = logging.Formatter('[%(asctime)s] %(name)s - %(levelname)s - %(message)s', "%H:%M:%S")
ch = logging.StreamHandler()
ch.setFormatter(formatter)
log.addHandler(ch)



class Scrapper:
    def __init__(self, headless: bool = False, user_data_dir: str = "./chromedata", log_level=logging.INFO):
        self.headless = headless
        self.user_data_dir = os.path.abspath(user_data_dir)
        self._pw_ctx = None
        self.playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self._target = None
        log.setLevel(log_level)
    
    async def sleep(self, seconds: float): 
        log.debug(f"Sleeping for {seconds} seconds")
        await asyncio.sleep(seconds)
        log.debug(f"Sleeping for {seconds} seconds")


    async def __aenter__(self) -> "Scrapper":
        self._pw_ctx = async_playwright()
        self.playwright = await self._pw_ctx.__aenter__()
        log.debug(f"Launching persistent context with user_data_dir={self.user_data_dir}, headless={self.headless}")
        self.context = await self.playwright.chromium.launch_persistent_context(
            self.user_data_dir,
            channel="chrome",
            headless=self.headless,
            no_viewport=True
        )
        pages = self.context.pages
        self.page = pages[0] if pages else await self.context.new_page()
        self.browser = None
        log.info("Stealth Scrapper ready!")
        return self

    async def __aexit__(self, exc_t, exc_v, exc_tb):
        # allow manual interaction before closing: do not block event loop
        loop = asyncio.get_running_loop()
        prompt = "Code is finished; Press enter to exit. Type 'debug' to enable debug mode for exit: "
        inp = await loop.run_in_executor(None, input, prompt)
        if isinstance(inp, str) and inp.lower() == "debug":
            log.setLevel(logging.DEBUG)


        log.debug("Exiting Scrapper context")
        if self.context:
            await self.context.close()
            log.debug("Closed context")
        if self._pw_ctx:
            await self._pw_ctx.__aexit__(exc_t, exc_v, exc_tb)
            log.debug("Closed playwright")
        log.info("Scrapper closed!")


    async def close(self):
        await self.__aexit__(None, None, None)

    async def open(self, url):
        log.debug(f"Opening page: {url}")
        page = await self.page.goto(url)
        if not (200 <= page.status < 300):
            log.warning(f"{url} : {page.status}")
        else:
            log.info(f"{url} : {page.status}")

        
    async def setJob(self, target):
        """Assign the target job to run (instance, class, or module)."""
        self._target = target
        log.debug(f"Target job assigned: {self._target}")

    async def start(self):
        if not self._target:
            raise RuntimeError("No target job assigned")
        log.debug(f"Target job is assigned: {self._target}")

        log.info(f"Starting target job: {self._target}")
        await self._target.start(self)
        log.info(f"Target job completed: {self._target}")
    

    async def currentScrollPos(self):
        x = await self.page.evaluate('() => window.scrollX')
        y = await self.page.evaluate('() => window.scrollY')
        return x, y

    def _ease_out_sine(self, t: float) -> float:
        return math.sin((t * math.pi) / 2)
    
    async def scroll(
        self,
        delta_x: int,
        delta_y: int,
        duration: float = 0.4,
        steps: int = 60,
        randomize: bool = True
    ):


        if randomize:
            delta_x += random.randint(-10, 10)
            delta_y += random.randint(-10, 10)
            log.debug(f"Randomized mouse move delta_x: {delta_x}, delta_y: {delta_y}")

        cX, cY = await self.currentScrollPos()
        log.debug(f"Scrolling mouse to delta_x: {delta_x}, delta_y: {delta_y}. Current scroll position X: {cX}, Y: {cY}")

        # Precompute eased deltas
        eased_steps = [self._ease_out_sine(i / steps) for i in range(1, steps + 1)]
        prev_dx, prev_dy = 0, 0

        for eased in eased_steps:
            target_dx = delta_x * eased
            target_dy = delta_y * eased

            move_dx = target_dx - prev_dx + random.uniform(-0.5, 0.5)
            move_dy = target_dy - prev_dy + random.uniform(-0.5, 0.5)

            # Only scroll if movement is meaningful
            if abs(move_dx) > 0.1 or abs(move_dy) > 0.1:
                await self.page.mouse.wheel(move_dx, move_dy)
 
            prev_dx = target_dx
            prev_dy = target_dy

            await asyncio.sleep(duration / steps)
        cX, cY = await self.currentScrollPos()
        log.debug(f"Scrolled mouse to delta_x: {delta_x}, delta_y: {delta_y}. New scroll position X: {cX}, Y: {cY}")

    async def soup(self, type = "html.parser") -> BeautifulSoup:
        return BeautifulSoup(await self.page.content(), type)

    async def attribSearch(self, root: PageElement, attribute: str, value: str) -> PageElement | None:
        if hasattr(root, 'get') and root.get(attribute) == value:
            log.debug(f"Found element with attribute '{attribute}' and value '{value}'")
            return root

        for child in getattr(root, 'children', []):
            if not hasattr(child, 'children'):
                continue

            result = await self.attribSearch(child, attribute, value)
            if result is not None:
                return result

        return None
    
    async def convertTag(self, tag: Tag) -> Locator:
        log.debug(f"Converting tag: {tag.name}")
        path = []
        while tag is not None and tag.name != '[document]':
            siblings = [sib for sib in tag.parent.find_all(tag.name, recursive=False)]
            if len(siblings) == 1:
                idx = ''
            else:
                idx = f'[{siblings.index(tag)+1}]'
            path.insert(0, f'/{tag.name}{idx}')
            tag = tag.parent

        path = '.' + ''.join(path)
        log.debug(f"Converted tag {tag.name} -> '{path}'")
        return self.page.locator(f'xpath={path}')
    

    async def updateTag(self, tag):
        """Given a BeautifulSoup tag, return the updated version of it from fresh soup using XPath."""

        def get_xpath(tag):
            elements = []
            current = tag
            while current and current.name and current.name != '[document]':
                siblings = current.find_previous_siblings(current.name)
                index = len(siblings) + 1
                elements.insert(0, f"{current.name}[{index}]")
                current = current.parent
            return "/" + "/".join(elements)

        def get_tag_by_xpath(soup, xpath):
            try:
                dom = etree.HTML(str(soup))
                element = dom.xpath(xpath)
                if element:
                    html_str = etree.tostring(element[0], encoding='unicode')
                    return BeautifulSoup(html_str, "html.parser").find()
            except Exception as e:
                log.error("XPath error:", e)
            return None

        xpath = get_xpath(tag)
        # print("Fixed XPath:", xpath)  # Debug

        soup = await self.soup()
        return get_tag_by_xpath(soup, xpath)

    # async def scrollTo(self, element: Locator | Tag, padding: int = 100, max_duration: float = 3.0, step_delay=0.016):
    #     """
    #     Smoothly scrolls to the element by animating mouse.wheel events until
    #     element is within `padding` pixels from top of viewport or max_duration is exceeded.
    #     """

    #     if isinstance(element, Tag):
    #         element = await self.convertTag(element)

    #     log.debug(f"Starting smooth scroll to element: {element}")

    #     start_time = asyncio.get_event_loop().time()

    #     # We'll do multiple small scroll steps until close or timeout
    #     while True:
    #         scroll_y, scroll_x = await self.currentScrollPos()
    #         element_y = await element.evaluate("el => el.getBoundingClientRect().top + window.scrollY")
    #         delta_y = element_y - scroll_y - padding

    #         log.debug(f"Current scrollY: {scroll_y}, elementY: {element_y}, deltaY needed: {delta_y}")

    #         if abs(delta_y) < 10:
    #             log.debug("Element within padding, stopping scroll.")
    #             break

    #         # Tween the scroll delta to a max step size to avoid big jumps
    #         max_step = 40  # max pixels per frame scroll (adjust for smoothness)
    #         step = max_step * self._ease_out_sine(min(1, abs(delta_y) / 300))
    #         step = step if delta_y > 0 else -step

    #         # Add some randomness to mimic natural scroll
    #         step += random.uniform(-1.5, 1.5)

    #         log.debug(f"Scrolling mouse wheel by delta_y step: {step:.2f}")

    #         await self.scroll(delta_x=0, delta_y=step)
    #         await asyncio.sleep(step_delay)  # ~60 FPS

    #         if asyncio.get_event_loop().time() - start_time > max_duration:
    #             log.warning(f"Max scroll duration {max_duration}s exceeded, stopping.")
    #             break


    async def scrollTo(
        self,
        element: Locator | Tag,
        duration: float = 0.4,
        steps: int = 60
    ):
        
        if isinstance(element, Tag):
            element = await self.convertTag(element)

        # Get element position relative to the document and viewport height
        box = await element.evaluate("""(el) => {
            const rect = el.getBoundingClientRect();
            return {
                top: rect.top + window.scrollY,
                height: rect.height,
                viewportHeight: window.innerHeight,
                scrollY: window.scrollY
            };
        }""")

        if box is None:
            log.warning(f"Element not found or not attached to DOM")

        # Calculate the target scroll position to center element vertically in viewport
        target_scroll_y = box["top"] + box["height"] / 2 - box["viewportHeight"] / 2

        # Clamp target_scroll_y to at least 0
        target_scroll_y = max(target_scroll_y, 0)

        # Get current scroll position
        current_scroll_y = box["scrollY"]

        total_delta_y = target_scroll_y - current_scroll_y

        last_dy = 0

        for step in range(1, steps + 1):
            t = step / steps
            eased = self._ease_out_sine(t)

            current_dy = total_delta_y * eased

            move_dy = current_dy - last_dy + random.uniform(-1, 1)
            move_dx = 0  # No horizontal scroll here, but you can add if needed

            await self.page.mouse.wheel(move_dx, move_dy)

            last_dy = current_dy

            await asyncio.sleep(duration / steps + random.uniform(-0.002, 0.002))

