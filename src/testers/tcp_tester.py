import asyncio
from typing import Optional, Dict
from .base_tester import BaseTester
from ..models.proxy import Proxy
from ..utils.constants import SUPPORTED_PROTOCOLS

class TCPTester(BaseTester):
    """TCP连接测试器"""
    
    @classmethod
    def get_tester_name(cls) -> str:
        return "tcp_tester"
    
    def __init__(self, logger=None, config: Dict = None):
        super().__init__(logger, config)
    
    async def test(self, proxy: Proxy, target_host: Optional[str] = None) -> bool:
        """
        测试TCP连接是否可用
        
        Args:
            proxy: 要测试的代理
            target_host: 目标主机（可选）
            
        Returns:
            bool: 连接成功返回True，否则返回False
        """
        if not self.is_enabled():
            return True  # 如果测试器被禁用，直接返回成功
            
        for attempt in range(self.retry_times):
            try:
                # 创建TCP连接
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(proxy.server, proxy.port),
                    timeout=self.connect_timeout
                )
                
                # 关闭连接
                writer.close()
                await writer.wait_closed()
                
                if self.logger:
                    self.logger.debug(f"TCP connection successful: {proxy.server}:{proxy.port}")
                return True
                
            except asyncio.TimeoutError:
                if self.logger:
                    self.logger.debug(f"TCP connection timeout: {proxy.server}:{proxy.port}")
                if attempt < self.retry_times - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                continue
                
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"TCP connection failed: {proxy.server}:{proxy.port} - {str(e)}")
                if attempt < self.retry_times - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                continue
        
        return False