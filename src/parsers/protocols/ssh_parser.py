from urllib.parse import urlparse, parse_qs
from .base_protocol_parser import BaseProtocolParser
from ...models.proxy import Proxy
from .protocol_parser_factory import ProtocolParserFactory
from ...utils.string_cleaner import StringCleaner
from ...utils.constants import (
    DEFAULT_VALUES,
    SPECIAL_CHARS,
    CLEAN_FIELDS,
    DEFAULT_PORTS,
    SSH_OPTIONS
)

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
            
            # 解析查询参数
            query_params = parse_qs(parsed.query)
            
            # 使用StringCleaner处理设置
            settings = {
                'username': StringCleaner.clean_value(username, 'username'),
                'password': password,
                'private_key': StringCleaner.clean_value(query_params.get('key', [''])[0], 'private_key'),
                'private_key_password': StringCleaner.clean_value(query_params.get('key_password', [''])[0], 'private_key_password'),
                'options': {}
            }
            
            # 处理SSH选项
            for key, value in query_params.items():
                if key.startswith('ssh_'):
                    option_name = key[4:]  # 移除'ssh_'前缀
                    settings['options'][option_name] = StringCleaner.clean_value(value[0], option_name)
            
            proxy = Proxy(
                raw_link=line,
                proxy_type='ssh',
                server=server,
                port=port,
                settings=settings
            )
            
            if self.logger:
                self.logger.debug(f"Successfully parsed SSH proxy: {server}:{port}")
            
            return proxy
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to parse SSH link: {str(e)}")
            raise ValueError(f"Invalid SSH link: {str(e)}")