from typing import Dict, Any, Optional
import asyncio
import socket
from .base_tester import BaseTester

class TCPTester(BaseTester):
    """TCP连接测试器"""
    
    def __init__(self, logger=None, connect_timeout: int = 5, retry_times: int = 2):
        super().__init__(logger)
        self.timeout = connect_timeout
        self.retry_times = retry_times
        
    def get_tester_name(self) -> str:
        return "TCP"
        
    async def test(self, proxy_info: Dict[str, Any], target_host: Optional[str] = None) -> bool:
        """测试TCP连接"""
        server = proxy_info["server"]
        port = proxy_info["port"]
        
        # 首先解析域名
        try:
            if not server.replace(".", "").isdigit():  # 如果不是IP地址
                server_ip = socket.gethostbyname(server)
            else:
                server_ip = server
        except Exception as e:
            if self.logger:
                self.logger.debug(f"DNS resolution failed for {server}: {str(e)}")
            return False
        
        for i in range(self.retry_times + 1):
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(server_ip, port),
                    timeout=self.timeout
                )
                writer.close()
                await writer.wait_closed()
                return True
            except Exception as e:
                if i == self.retry_times:
                    if self.logger:
                        self.logger.debug(f"TCP test failed for {server}({server_ip}):{port}: {str(e)}")
                    return False
                await asyncio.sleep(1)  # 重试前等待1秒
                continue
        return False