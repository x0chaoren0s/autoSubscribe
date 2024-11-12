import asyncio
import asyncssh
from typing import Dict
from pathlib import Path
from .base_tester import BaseTester
from ..models.proxy import Proxy

class SSHTester(BaseTester):
    """SSH连接测试器"""
    
    @classmethod
    def get_tester_name(cls) -> str:
        return "ssh_tester"
    
    def __init__(self, logger=None, config: Dict = None):
        super().__init__(logger, config)
        
        # 获取SSH特有配置
        self.key_path = self.get_config('key_path', '~/.ssh/id_rsa')
        self.known_hosts = self.get_config('known_hosts', False)
        self.command_timeout = self.get_config('command_timeout', 10)
        self.test_command = self.get_config('test_command', 'echo test')
    
    async def test(self, proxy: Proxy, target_host: str = None) -> bool:
        """测试SSH连接是否可用"""
        if not self.is_enabled():
            return True  # 如果测试器被禁用，直接返回成功
            
        if proxy.proxy_type != 'ssh':
            return False
            
        for attempt in range(self.retry_times):
            try:
                if self.logger:
                    self.logger.debug(f"Testing SSH proxy {proxy.server}:{proxy.port} (attempt {attempt + 1}/{self.retry_times})")
                
                # 获取SSH配置
                username = proxy.settings['username']
                password = proxy.settings.get('password', '')
                private_key = proxy.settings.get('private_key', '')
                key_password = proxy.settings.get('private_key_password', '')
                
                connect_kwargs = {
                    'username': username,
                    'port': proxy.port,
                    'connect_timeout': self.connect_timeout
                }
                
                # 设置认证方式
                if private_key:
                    key_path = Path(private_key).expanduser()
                    if not key_path.exists():
                        if self.logger:
                            self.logger.error(f"SSH key not found: {key_path}")
                        return False
                    try:
                        private_key = asyncssh.read_private_key(key_path, passphrase=key_password)
                        connect_kwargs['client_keys'] = [private_key]
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Failed to load SSH key: {str(e)}")
                        return False
                elif password:
                    connect_kwargs['password'] = password
                else:
                    if self.logger:
                        self.logger.error("No valid authentication method available")
                    return False
                
                # 设置SSH选项
                for key, value in proxy.settings.get('options', {}).items():
                    connect_kwargs[key.lower()] = value
                
                # 尝试连接并执行测试命令
                async with asyncssh.connect(proxy.server, **connect_kwargs) as conn:
                    try:
                        # 执行测试命令
                        result = await asyncio.wait_for(
                            conn.run(self.test_command, check=True),
                            timeout=self.command_timeout
                        )
                        if result.exit_status == 0:
                            if self.logger:
                                self.logger.debug(f"SSH connection successful: {proxy.server}:{proxy.port}")
                            return True
                        return False
                    except asyncio.TimeoutError:
                        if self.logger:
                            self.logger.error(f"SSH command timed out after {self.command_timeout}s")
                        return False
                    
            except asyncssh.DisconnectError as e:
                if self.logger:
                    self.logger.error(f"SSH connection failed: {str(e)}")
                if attempt < self.retry_times - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                continue
            except asyncssh.ProcessError as e:
                if self.logger:
                    self.logger.error(f"SSH command failed: {str(e)}")
                return False
            except Exception as e:
                if self.logger:
                    self.logger.error(f"SSH test failed: {str(e)}")
                if attempt < self.retry_times - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                continue
        
        return False