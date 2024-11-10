import aiohttp
import asyncio
from typing import Optional
from .base_fetcher import BaseFetcher

class HttpFetcher(BaseFetcher):
    """HTTP订阅源获取器"""
    
    def __init__(self, logger=None, timeout: int = 30, max_retries: int = 3, proxy: str = None):
        self.logger = logger
        self.timeout = timeout
        self.max_retries = max_retries
        self.proxy = proxy
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建HTTP会话"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0'
                }
            )
        return self._session
    
    async def fetch(self, url: str) -> str:
        """获取订阅内容"""
        session = await self._get_session()
        
        for attempt in range(self.max_retries):
            try:
                if self.logger:
                    self.logger.debug(f"Fetching {url}")
                    if self.proxy:
                        self.logger.debug(f"Using proxy: {self.proxy}")
                
                async with session.get(
                    url, 
                    ssl=False,
                    proxy=self.proxy,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        raise aiohttp.ClientError(
                            f"HTTP {response.status}: {response.reason}"
                        )
                    
                    content = await response.text()
                    if not content.strip():
                        raise ValueError("Empty response received")
                    
                    if self.logger:
                        self.logger.debug(f"Fetched content length: {len(content)}")
                        self.logger.debug(f"First 100 characters: {content[:100]}")
                    
                    return content
                    
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise
                
                wait_time = 2 ** attempt
                if self.logger:
                    self.logger.debug(f"Waiting {wait_time}s before retry")
                await asyncio.sleep(wait_time)
    
    async def close(self):
        """关闭HTTP会话"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理出口"""
        await self.close()
    