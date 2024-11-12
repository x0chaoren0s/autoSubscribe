import re
from urllib.parse import urlparse, parse_qs, unquote
from .base_protocol_parser import BaseProtocolParser
from ...models.proxy import Proxy
from .protocol_parser_factory import ProtocolParserFactory
from ...utils.string_cleaner import StringCleaner
from ...utils.constants import DEFAULT_VALUES

@ProtocolParserFactory.register
class VlessParser(BaseProtocolParser):
    # UUID格式的正则表达式
    UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
    
    @classmethod
    def protocol_prefix(cls) -> str:
        return 'vless://'
    
    def parse(self, line: str) -> Proxy:
        try:
            if self.logger:
                self.logger.debug(f"Parsing VLESS link: {line[:50]}...")
            
            # 移除前缀和注释部分
            vless_data = line[len(self.protocol_prefix()):]
            if '#' in vless_data:
                vless_data = vless_data.split('#')[0]
            
            # 解析URL
            if '@' in vless_data:
                uuid, server_info = vless_data.split('@', 1)
            else:
                raise ValueError("Missing UUID")
            
            # 验证UUID格式
            if not self.UUID_PATTERN.match(uuid):
                if self.logger:
                    self.logger.error(f"Invalid UUID format: {uuid}")
                raise ValueError("Invalid UUID format")
            
            # 处理服务器信息
            if '?' in server_info:
                server_port, params = server_info.split('?', 1)
            else:
                server_port = server_info
                params = ''
            
            # 解析服务器和端口
            if ':' in server_port:
                server, port = server_port.split(':', 1)
                # 移除可能的路径或查询参数
                port = port.split('/')[0].split('?')[0]
            else:
                server = server_port
                port = "443"  # 默认端口
            
            # 解析参数
            settings = {
                'uuid': uuid,
                'type': 'tcp',  # 默认值
                'security': 'none',  # 默认值
            }
            
            # 处理查询参数
            if params:
                param_pairs = params.split('&')
                for pair in param_pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        key = key.strip().lower()
                        value = unquote(value.strip())
                        settings[key] = value
            
            # 创建代理对象
            proxy = Proxy(
                raw_link=line,
                proxy_type='vless',
                server=server.strip(),
                port=int(port),
                settings=settings
            )
            
            if self.logger:
                self.logger.debug(f"Successfully parsed VLESS proxy: {server}:{port}")
            
            return proxy
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to parse VLESS link: {str(e)}")
            raise ValueError(f"Invalid vless link: {str(e)}")