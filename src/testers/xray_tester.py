import json
import asyncio
from typing import Dict, Any, Optional
import tempfile
import os
from .base_tester import BaseTester

class XrayTester(BaseTester):
    """Xray测试器"""
    
    def __init__(self, logger=None, timeout: int = 5, retry_times: int = 2, xray_path: str = "xray"):
        super().__init__(logger)
        self.timeout = timeout
        self.retry_times = retry_times
        self.xray_path = xray_path
        
    def get_tester_name(self) -> str:
        return "Xray"
        
    async def test(self, proxy_info: Dict[str, Any], target_host: Dict[str, Any]) -> bool:
        """使用Xray测试代理
        
        Args:
            proxy_info: 代理配置信息
            target_host: 目标站点配置，包含 host 和 check_url
        """
        # 跳过SSH代理
        if proxy_info["proxy_protocol"].value == "ssh":
            return False
            
        try:
            # 获取空闲端口
            listen_port = self._get_free_port()
            
            # 生成配置
            config = self._generate_config(proxy_info, listen_port)
            
            # 写入临时配置文件
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                json.dump(config, f)
                config_path = f.name
                
            try:
                # 启动Xray进程
                process = await asyncio.create_subprocess_exec(
                    self.xray_path,
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
                
                return success
                
            finally:
                # 终止进程
                if process:
                    process.terminate()
                    await process.wait()
                
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Xray test failed: {str(e)}")
            return False
            
        finally:
            # 清理临时文件
            try:
                os.unlink(config_path)
            except:
                pass
                
    def _generate_config(self, proxy_info: Dict[str, Any], listen_port: int) -> Dict:
        """生成Xray配置"""
        protocol = proxy_info["proxy_protocol"].value
        
        config = {
            "log": {
                "loglevel": "warning"
            },
            "inbounds": [
                {
                    "port": listen_port,
                    "listen": "127.0.0.1",
                    "protocol": "http",
                    "settings": {}
                }
            ],
            "outbounds": [
                {
                    "protocol": protocol,
                    "settings": self._generate_outbound_settings(proxy_info)
                }
            ]
        }
        
        return config
        
    def _generate_outbound_settings(self, proxy_info: Dict[str, Any]) -> Dict:
        """生成出站设置"""
        protocol = proxy_info["proxy_protocol"].value
        
        if protocol == "ss":
            return {
                "servers": [{
                    "address": proxy_info["server"],
                    "port": proxy_info["port"],
                    "method": proxy_info["method"],
                    "password": proxy_info["password"]
                }]
            }
            
        elif protocol == "vmess":
            return {
                "vnext": [{
                    "address": proxy_info["server"],
                    "port": proxy_info["port"],
                    "users": [{
                        "id": proxy_info["id"],
                        "alterId": proxy_info.get("aid", 0),
                        "security": proxy_info.get("security", "auto")
                    }]
                }]
            }
            
        elif protocol == "vless":
            return {
                "vnext": [{
                    "address": proxy_info["server"],
                    "port": proxy_info["port"],
                    "users": [{
                        "id": proxy_info["id"],
                        "encryption": proxy_info.get("encryption", "none")
                    }]
                }]
            }
            
        elif protocol == "trojan":
            return {
                "servers": [{
                    "address": proxy_info["server"],
                    "port": proxy_info["port"],
                    "password": proxy_info["password"]
                }]
            }
            
        raise ValueError(f"Unsupported protocol: {protocol}")
        