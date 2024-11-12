import asyncio
from typing import Dict
from pathlib import Path
from .base_tester import BaseTester
from ..models.proxy import Proxy
from ..utils.constants import SUPPORTED_PROTOCOLS

class GliderTester(BaseTester):
    """Glider测试器"""
    
    @classmethod
    def get_tester_name(cls) -> str:
        return "glider_tester"
    
    def __init__(self, logger=None, config: Dict = None):
        super().__init__(logger, config)
        
        # 获取glider特有配置
        self.check_url = self.get_config('check_url', 'http://www.msftconnecttest.com/connecttest.txt')
        self.check_expect = self.get_config('check_expect', '200')
        self.check_interval = self.get_config('check_interval', 30)
        self.check_timeout = self.get_config('check_timeout', 10)
        self.max_failures = self.get_config('max_failures', 3)
    
    async def test(self, proxy: Proxy, target_host: str) -> bool:
        """测试代理是否可用"""
        if not self.is_enabled():
            return True  # 如果测试器被禁用，直接返回成功
            
        for attempt in range(self.retry_times):
            try:
                # 获取空闲端口
                listen_port = self._get_free_port()
                
                # 生成测试配置
                test_config = [
                    "# Listener Settings",
                    f"listen=socks5://127.0.0.1:{listen_port}",  # 使用固定端口
                    "",
                    "# Forward Settings",
                    f"forward={proxy.to_glider_url()}",
                    "",
                    "# Check Settings",
                    "check=tcp",  # 使用TCP检查
                    f"checktarget={target_host}:80",  # 检查目标
                    f"checkinterval={self.check_interval}",
                    f"checktimeout={self.check_timeout}",
                    f"maxfailures={self.max_failures}"
                ]
                
                # 如果是SSH代理，添加超时设置
                if proxy.proxy_type == 'ssh':
                    test_config.insert(4, "timeout=5")  # SSH默认超时5秒
                
                # 保存测试配置
                test_config_file = Path(f"config/test_{proxy.server}_{proxy.port}.conf")
                with open(test_config_file, 'w', encoding='utf-8') as f:
                    f.write("\n".join(test_config))
                
                try:
                    # 启动Glider进程
                    glider_path = self.get_config('path', 'glider')
                    process = await asyncio.create_subprocess_exec(
                        glider_path,
                        '-config',
                        str(test_config_file),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    try:
                        # 等待glider启动
                        await asyncio.sleep(1)
                        
                        # 使用基类的SOCKS5测试方法
                        if await self._test_socks5(listen_port, target_host):
                            if self.logger:
                                self.logger.debug(f"Test passed: {proxy.server}:{proxy.port}")
                            return True
                        return False
                            
                    finally:
                        # 终止glider进程
                        process.kill()
                        await process.wait()
                        
                finally:
                    # 清理测试配置文件
                    try:
                        test_config_file.unlink()
                    except:
                        pass
                        
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"Test error: {str(e)}")
                if attempt < self.retry_times - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                continue
        
        return False