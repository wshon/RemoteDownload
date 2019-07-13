import aiohttp
import async_timeout
from aiohttp import web, InvalidURL


async def fetch(session, url):
    async with async_timeout.timeout(60):
        async with session.get(url) as response:
            return await response.read()


async def handle(request):
    return web.Response(text=f'''Usage: 
    
{request.url.parent}<url>
''')


async def handle_download(request):
    url = request.match_info.get('url', 'http://www.w3school.com.cn/i/movie.mp4')
    async with aiohttp.ClientSession() as session:
        try:
            content = await fetch(session, url)
            return web.Response(body=content)
        except InvalidURL:
            return web.Response(text=f'URL_ERROR: {url}')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([web.get('/', handle),
                    web.get(r'/{url:.*}', handle_download)])
    web.run_app(app)
