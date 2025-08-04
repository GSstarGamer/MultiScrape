import asyncio
import traceback
from post_scrapper import Scrapper
from post_scrapper.targets.facebook import Facebook
import logging


async def main():
    try:
        async with Scrapper() as s:
            fb = Facebook("Razer", mentions=True)
            await s.setJob(fb)
            await s.start()
    

            
    except Exception:
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
