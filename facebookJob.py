import asyncio
import traceback
from post_scrapper import Scrapper
from post_scrapper.targets.facebookBetter import FacebookBetter
import logging


async def main():
    try:
        async with Scrapper() as s:
            fb = FacebookBetter("Razer", recent=True, mentions=False)
            await s.setJob(fb)
            await s.start()
    
            
    except Exception:
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
