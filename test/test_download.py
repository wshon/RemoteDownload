import asyncio
import os

from downloader import DownloadWrapper


async def fun():
    url = 'https://dldir1.qq.com/qqfile/qq/PCTIM2.3.2/21158/TIM2.3.2.21158.exe'
    filename = os.path.basename(url)
    download = DownloadWrapper()
    res = await download(url, filename)
    print("已经开始下载", res)


loop = asyncio.get_event_loop()
loop.run_until_complete(fun())
