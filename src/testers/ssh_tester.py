from typing import Dict, Any, Optional
import asyncio
import asyncssh
from .base_tester import BaseTester

class SSHTester(BaseTester):
    """SSH测试器"""
    
    def __init__(self, logger=None, timeout: int = 5, retry_times: int = 2):
        super().__init__(logger)
        self.timeout = timeout
        self.retry_times = retry_times
        
    def get_tester_name(self) -> str:
        return "SSH"
        
    async def test(self, proxy_info: Dict[str, Any], target_host: Optional[str] = None) -> bool:
        """测试SSH连接"""
        if proxy_info["proxy_protocol"].value != "ssh":
            return False
            
        server = proxy_info["server"]
        port = proxy_info["port"]
        username = proxy_info.get("username", "")
        password = proxy_info.get("password", "")
        private_key = proxy_info.get("private_key", "")
        
        for i in range(self.retry_times + 1):
            try:
                if private_key:
                    key = asyncssh.import_private_key(private_key)
                    conn = await asyncio.wait_for(
                        asyncssh.connect(
                            server,
                            port=port,
                            username=username,
                            client_keys=[key],
                            known_hosts=None
                        ),
                        timeout=self.timeout
                    )
                else:
                    conn = await asyncio.wait_for(
                        asyncssh.connect(
                            server,
                            port=port,
                            username=username,
                            password=password,
                            known_hosts=None
                        ),
                        timeout=self.timeout
                    )
                conn.close()
                return True
            except Exception as e:
                if i == self.retry_times:
                    if self.logger:
                        self.logger.debug(f"SSH test failed for {server}:{port}: {str(e)}")
                    return False
                continue
        return False