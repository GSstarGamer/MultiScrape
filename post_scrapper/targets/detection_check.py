from ..scrapper import Scrapper
import inspect
import asyncio

class detectionCheck():
    def __init__(self):
        self._pass = 0
        self._fail = 0
        pass

    def __str__(self):
        return f"detectionCheck()"

    async def start(self, Scrapper: Scrapper):
        page = Scrapper.page

        # fingerprint.com
        await Scrapper.open("https://fingerprint.com/products/bot-detection/")
        await page.wait_for_selector('h3[class^="HeroSection-module--botSubTitle"]', timeout=20000)
        element = await Scrapper.page.query_selector('h3[class^="HeroSection-module--botSubTitle"]')
        if element:
            text = await element.text_content()
            if text == "You are a bot":
                print("fingerprint.com failed")
                self._fail += 1
            else:
                print("fingerprint.com passed")
                self._pass += 1
            
        

        # iphey.com
        await Scrapper.open("https://iphey.com/")

        await page.wait_for_function("""
            () => {
                const loader = document.querySelector('.loader');
                return loader && loader.classList.contains('hide');
            }
        """, timeout=15000)


        status_map = {
            "trustworthy": "Good",
            "suspicious": "Suspicious",
            "unreliable": "Bot"
        }

        final_status = "Unknown"
        for key, label in status_map.items():
            locator = page.locator(f".identity-status__status.{key}")
            if await locator.is_visible():
                final_status = label
                break
        
        if final_status == "Good":
            print("iphey.com passed")
            self._pass += 1
        else:
            print("iphey.com failed, status:", final_status)
            self._fail += 1
        

        # browserscan.net
        await page.goto("https://www.browserscan.net/bot-detection")

        await page.wait_for_selector("strong:text('Test Results:')", timeout=15000)

        robot_label = page.locator("//strong[text()='Test Results:']/following-sibling::strong[1]").first
        text = await robot_label.text_content()

        await page.screenshot(path="bot.png", full_page=True)

        if text == "Normal":
            print("browserscan.net passed")
            self._pass += 1
        else:
            print("browserscan.net failed")
            self._fail += 1
        
        
        print("Bot Detection Checks:", self._pass, "pass", self._fail, "fail")
