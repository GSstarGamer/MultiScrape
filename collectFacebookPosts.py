import asyncio
import traceback
from post_scrapper import Scrapper
from post_scrapper.targets.facebookPosts import FacebookBetter, Post  # Post for typing / use
import logging


async def on_new_post(post: Post):
    print("POST")
    print("User:     ", post.username)
    print("URL:      ", post.post_url)
    print("Epoch:    ", post.epoch)
    print("Reactions:", post.reactions)
    print("Content:  ", post.content)
    print()

async def main():
    try:
        async with Scrapper() as s:
            fb = FacebookBetter("Razer", recent=True, mentions=False, on_post=on_new_post)
            # s.log.setLevel(logging.DEBUG)
            await s.setJob(fb)
            await s.start() 
    except Exception:
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
