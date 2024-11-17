import aiohttp
import os
from typing import Optional
from .base_fetcher import BaseFetcher

class HttpFetcher(BaseFetcher):
    """HTTP获取器"""
    
    def __init__(self, logger=None, connect_timeout: int = 10, max_retries: int = 3, proxy: Optional[dict] = None):
        super().__init__(logger)
        self.connect_timeout = connect_timeout
        self.max_retries = max_retries
        self.proxy = proxy
        
    async def fetch(self, url: str) -> Optional[str]:
        """获取URL内容
        
        支持:
        - HTTP/HTTPS URL
        - 本地文件路径（相对于项目根目录）
        """
        # 检查是否是本地文件
        if not url.startswith(('http://', 'https://')):
            try:
                # 尝试作为相对路径读取
                with open(url, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"Failed to read local file {url}: {str(e)}")
                return None
        
        # HTTP/HTTPS URL
        for i in range(self.max_retries + 1):
            try:
                # 配置代理
                proxy = None
                if self.proxy and self.proxy.get("enabled"):
                    proxy = self.proxy.get("url")
                
                # 创建会话
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=self.connect_timeout),
                        proxy=proxy,
                        ssl=False  # 忽略SSL证书验证
                    ) as response:
                        if response.status == 200:
                            content = await response.text()
                            if content:
                                return content
                            if self.logger:
                                self.logger.debug(f"Empty response from {url}")
                        else:
                            if self.logger:
                                self.logger.debug(f"HTTP {response.status} from {url}")
                            continue
            except Exception as e:
                if i == self.max_retries:
                    if self.logger:
                        self.logger.debug(f"Failed to fetch {url}: {str(e)}")
                    return None
                continue
        return None
    