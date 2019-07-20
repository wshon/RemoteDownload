import asyncio
import hashlib
import logging
import os
import sys
from datetime import datetime

import aiofiles
from aiohttp import web, InvalidURL
from aiohttp.web_urldispatcher import AbstractResource

from downloader import DownloadWrapper

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))


async def handle(request):
    return web.Response(text=f'''Usage: 
    
{request.url.parent}<url>
''')


async def handle_file(request):
    async with aiofiles.open(f'.{request.path}', 'rb') as f:
        content = await f.read()
    return web.Response(
        body=content,
        headers={'Content-Disposition': f'attachment; filename="{request.query.get("filename")}"'},
        content_type='application/octet-stream')


async def handle_download(request):
    url = request.match_info.get('url', 'http://www.w3school.com.cn/i/movie.mp4')

    try:
        download = DownloadWrapper()

        filepath = os.path.dirname(url)
        md5 = hashlib.md5()
        md5.update(filepath.encode("utf-8"))
        filepath_md5 = md5.hexdigest()

        filename = os.path.basename(url)
        md5 = hashlib.md5()
        md5.update(filename.encode("utf-8"))
        filename_md5 = md5.hexdigest()

        full_path = os.path.join('file', filepath_md5)
        if not os.path.exists(full_path):
            os.makedirs(full_path)
        full_name = os.path.join(full_path, filename_md5)

        last_futuer = request.app.get('file', {}).get(filepath_md5, {}).get(filename_md5, None)
        if last_futuer:
            logger.debug('Last future found, now waiting...')
            last_res = await last_futuer
            logger.debug(f'Last future result is {last_res}')
        else:
            logger.debug('Last future not found.')
            last_res = False

        if not last_res:
            logger.debug('Start new download.')
            download_done = asyncio.Future()
            request.app['file'] = {filepath_md5: {filename_md5: download_done}}
            try:
                await download(url, full_name)
                async with aiofiles.open(f'{full_name}.name', "w") as f:
                    await f.write(filename)
                async with aiofiles.open(f'{full_name}.time', "w") as f:
                    await f.write(datetime.now().strftime('%Y.%m.%d %H:%M:%S'))

                logger.debug('Download finish, set future [True].')
                download_done.set_result(True)
            except Exception:
                logger.exception('Download fail, set future [False].')
                download_done.set_result(False)

        router = request.app.router['url']  # type: AbstractResource
        return web.HTTPFound(router.url_for(path=filepath_md5, name=filename_md5).with_query(filename=filename))

    except InvalidURL:
        return web.Response(text=f'URL_ERROR: {url}')


app = web.Application()
app.router.add_get('/', handle)
app.router.add_get('/file/{path}/{name}', handle_file, name='url')
app.router.add_get(r'/{url:((http|ftp|https)://).*}', handle_download)

if __name__ == '__main__':
    web.run_app(app)
