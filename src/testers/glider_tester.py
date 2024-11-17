from typing import Dict, Any, Optional
import asyncio
import tempfile
import os
from .base_tester import BaseTester
from src.decoders.glider_decoder import GliderDecoder

class GliderTester(BaseTester):
    """Glider测试器"""
    
    def __init__(self, logger=None, config: Dict = None):
        super().__init__(logger)
        self.config = config or {}
        
    def get_tester_name(self) -> str:
        return "Glider"
        
    async def test(self, proxy_info: Dict[str, Any], target_host: Optional[str] = None) -> bool:
        """使用Glider测试代理"""
        try:
            # 转换为glider链接
            glider_link = GliderDecoder.decode(proxy_info)
            
            # 获取空闲端口
            listen_port = self._get_free_port()
            
            # 生成临时配置文件
            config = self._generate_config(glider_link, target_host, listen_port)
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write(config)
                config_path = f.name
                
            # 启动Glider进程
            process = await asyncio.create_subprocess_exec(
                "glider",
                "-config", config_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 等待进程启动
            await asyncio.sleep(1)
            
            # 测试连接
            success = await self._test_connection(
                target_host["check_url"],  # 使用目标站点的check_url
                listen_port
            )
            
            # 终止进程
            process.terminate()
            await process.wait()
            
            return success
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Glider test failed: {str(e)}")
            return False
            
        finally:
            # 清理临时文件
            try:
                os.unlink(config_path)
            except:
                pass
                
    def _generate_config(self, forward: str, target_host: Optional[str], listen_port: int) -> str:
        """生成Glider配置"""
        config_lines = [
            "verbose=True",
            f"listen=:{listen_port}",
            f"forward={forward}",
            f"check={target_host['check_url']}",
            f"checkinterval={self.config.get('check_interval', 30)}",
        ]
        return "\n".join(config_lines)
        