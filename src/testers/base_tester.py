import socket
import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import aiohttp

class BaseTester(ABC):
    """代理测试器的基类"""
    
    _logger = None  # 类级别的logger
    
    def __init__(self, logger=None, config: Dict = None):
        """
        初始化测试器
        
        Args:
            logger: 日志记录器
            config: 配置字典，包含以下结构：
                {
                    'testers': {
                        'concurrent_tests': int,  # 默认并发数
                        'connect_timeout': int,   # 默认连接超时
                        'retry_times': int,       # 默认重试次数
                        'tester_name': {          # 具体测试器的配置
                            'enabled': bool,      # 是否启用
                            'concurrent_tests': int,  # 覆盖默认并发数
                            'connect_timeout': int,   # 覆盖默认超时
                            'retry_times': int,       # 覆盖默认重试次数
                            ...                       # 其他特有配置
                        }
                    }
                }
        """
        self.logger = logger
        self.__class__._logger = logger  # 设置类级别的logger
        
        # 获取配置
        self.config = config or {}
        testers_config = self.config.get('testers', {})
        
        # 获取默认值
        self.concurrent_tests = testers_config.get('concurrent_tests', 5)
        self.connect_timeout = testers_config.get('connect_timeout', 10)
        self.retry_times = testers_config.get('retry_times', 2)
        
        # 获取具体测试器的配置
        tester_config = testers_config.get(self.get_tester_name(), {})
        
        # 覆盖默认值（如果有配置）
        if tester_config:
            self.concurrent_tests = tester_config.get('concurrent_tests', self.concurrent_tests)
            self.connect_timeout = tester_config.get('connect_timeout', self.connect_timeout)
            self.retry_times = tester_config.get('retry_times', self.retry_times)
    
    @classmethod
    @abstractmethod
    def get_tester_name(cls) -> str:
        """返回测试器的名称（用于配置）"""
        pass
    
    def _get_free_port(self) -> int:
        """获取一个空闲的端口号"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    async def _test_socks5(self, port: int, target_host: str) -> bool:
        """通过SOCKS5协议测试连接"""
        try:
            reader, writer = await asyncio.open_connection('127.0.0.1', port)
            
            # SOCKS5握手
            writer.write(b'\x05\x01\x00')  # 版本5，1个认证方法，无认证
            await writer.drain()
            
            auth_response = await reader.read(2)
            if auth_response != b'\x05\x00':
                raise Exception("SOCKS5 authentication failed")
            
            # 发送连接请求
            writer.write(b'\x05\x01\x00\x01' + socket.inet_aton(target_host) + b'\x00\x50')  # TCP连接，IPv4，80端口
            await writer.drain()
            
            conn_response = await reader.read(10)
            if conn_response[1] != 0:
                raise Exception(f"SOCKS5 connection failed: {conn_response[1]}")
            
            # 连接成功
            writer.close()
            await writer.wait_closed()
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"SOCKS5 test failed: {str(e)}")
            return False
    
    @abstractmethod
    async def test(self, proxy_info: Dict[str, Any], target_host: Optional[str] = None) -> bool:
        """测试代理可用性
        
        Args:
            proxy_info: 代理元信息字典
            target_host: 目标主机（可选）
            
        Returns:
            bool: 测试是否成功
        """
        pass

    async def _test_connection(self, url: str, port: int) -> bool:
        """测试代理连接
        
        Args:
            url: 目标URL
            port: 本地代理端口
            
        Returns:
            bool: 连接是否成功
        """
        try:
            # 使用curl命令测试连接
            process = await asyncio.create_subprocess_exec(
                "curl",
                url,
                "--proxy", f"http://127.0.0.1:{port}",
                "-k",  # 忽略SSL证书验证
                "-s",  # 静默模式
                "-o", "/dev/null",  # 不输出内容
                "-w", "%{http_code}",  # 只输出状态码
                "--connect-timeout", "10",  # 连接超时
                "--max-time", "15",  # 总超时
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 等待结果
            stdout, stderr = await process.communicate()
            
            # 检查状态码
            if process.returncode == 0:
                status_code = int(stdout.decode().strip())
                return 200 <= status_code < 400
                
            if self.logger:
                self.logger.debug(f"Curl failed with return code {process.returncode}")
                if stderr:
                    self.logger.debug(f"Curl error: {stderr.decode()}")
            return False
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Connection test failed: {str(e)}")
            return False
    
    def is_enabled(self) -> bool:
        """检查测试器是否启用"""
        return self.config.get('testers', {}).get(self.get_tester_name(), {}).get('enabled', True)
    
    def get_config(self, key: str, default=None):
        """获取测试器的特定配置"""
        return self.config.get('testers', {}).get(self.get_tester_name(), {}).get(key, default)