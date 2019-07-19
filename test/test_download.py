import asyncio

from downloader import DownloadWrapper


async def fun():
    download = DownloadWrapper()
    await download('https://dldir1.qq.com/qqfile/qq/PCTIM2.3.2/21158/TIM2.3.2.21158.exe', 'download.file')
    print("已经开始下载")


loop = asyncio.get_event_loop()
loop.run_until_complete(fun())
