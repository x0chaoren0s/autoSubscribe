from urllib.parse import urlparse
from .base_protocol_parser import BaseProtocolParser
from ...models.proxy import Proxy
from .protocol_parser_factory import ProtocolParserFactory

@ProtocolParserFactory.register
class SSHParser(BaseProtocolParser):
    @classmethod
    def protocol_prefix(cls) -> str:
        return 'ssh://'
    
    def parse(self, line: str) -> Proxy:
        try:
            if self.logger:
                self.logger.debug(f"Parsing SSH link: {line[:50]}...")
                
            parsed = urlparse(line)
            
            # 解析认证信息
            if '@' in parsed.netloc:
                credentials, host_port = parsed.netloc.split('@')
                if ':' in credentials:
                    username, password = credentials.split(':')
                else:
                    username = credentials
                    password = ''
                if self.logger:
                    self.logger.debug(f"Found credentials: username={username}")
            else:
                host_port = parsed.netloc
                username = 'root'  # 默认用户名
                password = ''
                if self.logger:
                    self.logger.debug("Using default credentials")
            
            # 解析服务器和端口
            if ':' in host_port:
                server, port = host_port.split(':')
                port = int(port)
            else:
                server = host_port
                port = 22  # SSH默认端口
                if self.logger:
                    self.logger.debug("Using default SSH port 22")
            
            settings = {
                'username': username,
                'password': password,
                'private_key': parsed.query.get('key', ''),
                'private_key_password': parsed.query.get('key_password', '')
            }
            
            proxy = Proxy(
                raw_link=line,
                proxy_type='ssh',
                server=server,
                port=port,
                settings=settings
            )
            
            if self.logger:
                self.logger.debug(f"Successfully parsed SSH proxy: {server}:{port}")
                self.logger.debug(f"Settings: {settings}")
            
            return proxy
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to parse SSH link: {str(e)}")
            raise ValueError(f"Invalid SSH link: {str(e)}") 