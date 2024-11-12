import aiohttp
import asyncio
from typing import Optional, Dict
from .base_fetcher import BaseFetcher

class HttpFetcher(BaseFetcher):
    """HTTP订阅源获取器"""
    
    def __init__(self, logger=None, config: Dict = None):
        super().__init__(logger, config)
        self._session: Optional[aiohttp.ClientSession] = None
        self.proxy = self.get_config('proxy')  # 可选的代理设置
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建HTTP会话"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    'User-Agent': self.user_agent,
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Connection': 'keep-alive'
                }
            )
        return self._session
    
    async def fetch(self, url: str) -> str:
        """获取订阅内容"""
        session = await self._get_session()
        
        for attempt in range(self.retry_times):
            try:
                async with session.get(
                    url,
                    proxy=self.proxy,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    allow_redirects=True,
                    verify_ssl=not self.get_config('skip_ssl_verify', False)
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
                if attempt == self.retry_times - 1:
                    raise
                
                wait_time = 2 ** attempt
                if self.logger:
                    self.logger.debug(f"Waiting {wait_time}s before retry")
                await asyncio.sleep(wait_time)
    
    async def close(self):
        """关闭HTTP会话"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    