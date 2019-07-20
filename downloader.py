# -*- coding:utf-8 -*-
# from https://github.com/ShichaoMa/async-downloader
import json
import logging
import os
import re
import sys

import aiofiles
import aiohttp
from aiohttp import ClientPayloadError


async def readexactly(steam, n):
    if steam._exception is not None:
        raise steam._exception

    blocks = []
    while n > 0:
        block = await steam.read(n)
        if not block:
            break
        blocks.append(block)
        n -= len(block)

    return b''.join(blocks)


class DownloadWrapper(object):

    def __init__(self, download_method=None, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.default_engine_cls = DownloaderEngine
        self.download_method = download_method

    async def close(self):
        pass

    async def __call__(self, *args, **kwargs):
        if self.download_method:
            return await self.download_method(*args, **kwargs)
        else:
            engine = self.default_engine_cls(*self.args, **self.kwargs)
            try:
                return await engine.run(*args, **kwargs)
            finally:
                await engine.close()


class DownloaderEngine(object):
    """
    支持断点续传
    """
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en',
        'Accept-Encoding': 'deflate, gzip'
    }

    def __init__(self, proxy=None, proxy_auth=None, conn_timeout=10, read_timeout=1800):
        self.proxy = proxy
        self.proxy_auth = proxy_auth
        self.session = aiohttp.ClientSession(conn_timeout=conn_timeout, read_timeout=read_timeout)
        self.failed_times_max = 3
        self.tries = 0
        self.logger = self.logger()

    def logger(self):
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(10)
        logger.addHandler(logging.StreamHandler(sys.stdout))
        return logger

    async def run(self, url, filename, failed_times=0):
        if failed_times > self.failed_times_max:
            self.logger.error(f"Abandon {filename} of {url} failed for {failed_times} times.")
            return
        received, total, f = 0, 0, None
        if os.path.exists(filename) and await self.conti_check(url):
            f = await aiofiles.open(filename, "ab")
            received = await f.tell()

        while self.tries < 2:
            headers = self.headers.copy()
            try:
                while True:
                    headers["Range"] = f"bytes={received}-"
                    self.logger.debug(f"File {filename} got {received} bytes.")
                    resp = None
                    try:
                        resp = await self.session.request("GET", url, headers=headers, **self.get_proxy())
                        # 下载文件
                        if int(resp.headers['Content-Length']) == 0:
                            self.logger.info(f"{filename} download finished. ")
                            break
                        content_range = resp.headers['Content-Range']
                        total = int(re.search(r'/(\d+)', content_range).group(1))
                        total = total or content_range
                        if content_range and resp.status < 300:
                            f = f or await aiofiles.open(filename, "wb")
                            chunk = await readexactly(resp.content, 1024 * 1024)
                            while chunk:
                                received += len(chunk)
                                self.logger.debug(
                                    f"Download {filename}: {len(chunk)} from {url}"
                                    f", processing {round(received / total * 100, 2)}. ")
                                await f.write(chunk)
                                chunk = await readexactly(resp.content, 1024 * 1024)
                            self.logger.info(f"File {filename} download finished. ")
                            break
                        else:
                            raise RuntimeError(f"Haven't got any data from {url}.")
                    except ClientPayloadError:
                        self.logger.error(f"File {filename} download error, try to continue. ")
                    finally:
                        resp and resp.close()
                break
            except Exception as e:
                self.logger.exception(f"File {filename} got Error: {e}")
                self.tries += 1
        else:
            f and f.close()
            failed_times += 1
            self.logger.error(f"File {filename} of {url} failed for {failed_times} times.")
            return json.dumps({"url": url, "filename": filename, "failed_times": failed_times})

    def get_proxy(self):
        if self.tries % 2:
            return {
                "proxy": self.proxy,
                "proxy_auth": self.proxy_auth and aiohttp.BasicAuth(*self.proxy_auth)
            }
        else:
            return {"proxy": None, "proxy_auth": None}

    async def conti_check(self, url):
        while True:
            try:
                headers = self.headers.copy()
                headers['Range'] = 'bytes=0-4'
                resp = await self.session.request("GET", url, headers=headers, **self.get_proxy())
                return bool(resp.headers.get('Content-Range'))
            except Exception as e:
                self.logger.exception(f"Failed to check: {e}")
                if self.tries < 2:
                    self.tries += 1
                else:
                    raise e

    async def close(self):
        return await self.session.close()
