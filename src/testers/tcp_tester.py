import asyncio
import socket
from .base_tester import BaseTester
from ..models.proxy import Proxy

class TCPTester(BaseTester):
    """TCP连接测试器"""
    
    def __init__(self, logger=None, timeout: float = 3, retry_times: int = 2):
        super().__init__(logger)
        self.timeout = timeout
        self.retry_times = retry_times
    
    async def test(self, proxy: Proxy, target_host: str = None) -> bool:
        """测试TCP连接是否可用"""
        for attempt in range(self.retry_times):
            try:
                # 创建future对象
                future = self._tcp_connect(proxy.server, proxy.port)
                # 等待连接完成或超时
                await asyncio.wait_for(future, timeout=self.timeout)
                if self.logger:
                    self.logger.debug(f"TCP connection successful to {proxy.server}:{proxy.port}")
                return True
                
            except (asyncio.TimeoutError, ConnectionRefusedError, socket.gaierror) as e:
                if self.logger:
                    self.logger.debug(f"TCP connection attempt {attempt + 1} failed to {proxy.server}:{proxy.port}: {str(e)}")
                    
                # 如果不是最后一次尝试，等待一下再重试
                if attempt < self.retry_times - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    if self.logger:
                        self.logger.debug(f"Waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"Unexpected error during TCP connection attempt {attempt + 1} to {proxy.server}:{proxy.port}: {str(e)}")
                    
                # 如果不是最后一次尝试，等待一下再重试
                if attempt < self.retry_times - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    if self.logger:
                        self.logger.debug(f"Waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
        
        return False

    async def _tcp_connect(self, server: str, port: int):
        """异步TCP连接"""
        loop = asyncio.get_event_loop()
        await loop.create_connection(
            lambda: asyncio.Protocol(),
            server,
            port
        )