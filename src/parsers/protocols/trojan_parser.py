from urllib.parse import urlparse, parse_qs, unquote
from .base_protocol_parser import BaseProtocolParser
from ...models.proxy import Proxy
from .protocol_parser_factory import ProtocolParserFactory
from ...utils.string_cleaner import StringCleaner
from ...utils.constants import DEFAULT_VALUES

@ProtocolParserFactory.register
class TrojanParser(BaseProtocolParser):
    @classmethod
    def protocol_prefix(cls) -> str:
        return 'trojan://'
    
    def parse(self, line: str) -> Proxy:
        try:
            if self.logger:
                self.logger.debug(f"Parsing Trojan link: {line[:50]}...")
            
            # 移除前缀和注释部分
            trojan_data = line[len(self.protocol_prefix()):]
            if '#' in trojan_data:
                trojan_data = trojan_data.split('#')[0]
            
            # 解析URL
            if '@' in trojan_data:
                password, server_info = trojan_data.split('@', 1)
            else:
                raise ValueError("Missing password")
            
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
                'password': password.strip(),
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
                        
                        # 验证SNI的有效性
                        if key == 'sni':
                            # 如果SNI包含非法字符
                            if any(c in value for c in [',', ';','#', '?', '@', ' ']):
                                if self.logger:
                                    self.logger.error(f"Invalid SNI value (contains invalid chars): {value}")
                                raise ValueError("Invalid SNI value")
                        
                        settings[key] = value
            
            # 创建代理对象
            proxy = Proxy(
                raw_link=line,
                proxy_type='trojan',
                server=server.strip(),
                port=int(port),
                settings=settings
            )
            
            if self.logger:
                self.logger.debug(f"Successfully parsed Trojan proxy: {server}:{port}")
            
            return proxy
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to parse Trojan link: {str(e)}")
            raise ValueError(f"Invalid trojan link: {str(e)}")