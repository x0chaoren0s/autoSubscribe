import json
import asyncio
from typing import Dict
from pathlib import Path
from .base_tester import BaseTester
from ..models.proxy import Proxy
from ..utils.constants import SUPPORTED_PROTOCOLS

class XrayTester(BaseTester):
    """Xray测试器"""
    
    @classmethod
    def get_tester_name(cls) -> str:
        return "xray_tester"
    
    def __init__(self, logger=None, config: Dict = None):
        super().__init__(logger, config)
    
    async def test(self, proxy: Proxy, target_host: str) -> bool:
        """测试代理是否可用"""
        if not self.is_enabled():
            return True  # 如果测试器被禁用，直接返回成功
            
        if proxy.proxy_type not in SUPPORTED_PROTOCOLS or proxy.proxy_type == 'ssh':
            return False
            
        for attempt in range(self.retry_times):
            try:
                # 获取空闲端口
                socks_port = self._get_free_port()
                
                # 生成测试配置
                test_config = {
                    "inbounds": [{
                        "port": socks_port,
                        "listen": "127.0.0.1",
                        "protocol": "socks",  # 使用SOCKS协议
                        "settings": {
                            "auth": "noauth",
                            "udp": True
                        }
                    }],
                    "outbounds": [{
                        "protocol": "shadowsocks" if proxy.proxy_type == "ss" else proxy.proxy_type,
                        "settings": self._generate_proxy_settings(proxy),
                        "streamSettings": self._generate_stream_settings(proxy)
                    }]
                }
                
                # 保存测试配置
                test_config_file = Path(f"config/test_{proxy.server}_{proxy.port}.json")
                with open(test_config_file, 'w', encoding='utf-8') as f:
                    json.dump(test_config, f, indent=2, ensure_ascii=False)
                
                try:
                    # 启动Xray进程
                    xray_path = self.get_config('path', 'xray')
                    process = await asyncio.create_subprocess_exec(
                        xray_path,
                        '-config',
                        str(test_config_file),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    try:
                        # 等待xray启动
                        await asyncio.sleep(1)
                        
                        # 使用基类的SOCKS5测试方法
                        if await self._test_socks5(socks_port, target_host):
                            if self.logger:
                                self.logger.debug(f"Test passed: {proxy.server}:{proxy.port}")
                            return True
                        return False
                            
                    finally:
                        # 终止xray进程
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
    
    def _generate_proxy_settings(self, proxy: Proxy) -> Dict:
        """生成代理设置"""
        # ... (保持不变)
    
    def _generate_stream_settings(self, proxy: Proxy) -> Dict:
        """生成传输层设置"""
        # ... (保持不变)