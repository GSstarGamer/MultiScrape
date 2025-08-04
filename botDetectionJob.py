import asyncio
import traceback
from post_scrapper import Scrapper
from post_scrapper.targets.detection_check import detectionCheck
import logging


async def main():
    try:
        async with Scrapper(headless=False) as s:
            job = detectionCheck()
            await s.setJob(job)
            await s.start()
            
    except Exception:
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
