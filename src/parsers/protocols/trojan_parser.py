from urllib.parse import urlparse, parse_qs, unquote
from .base_protocol_parser import BaseProtocolParser
from ...models.proxy import Proxy
from .protocol_parser_factory import ProtocolParserFactory

@ProtocolParserFactory.register
class TrojanParser(BaseProtocolParser):
    @classmethod
    def protocol_prefix(cls) -> str:
        return 'trojan://'
    
    def parse(self, line: str) -> Proxy:
        try:
            if self.logger:
                self.logger.debug(f"Parsing Trojan link: {line[:50]}...")
            
            # 移除前缀
            trojan_data = line[len(self.protocol_prefix()):]
            
            try:
                # 处理URL编码
                trojan_data = unquote(trojan_data)
                
                # 解析URL
                if '@' not in trojan_data:
                    # 处理没有@符号的情况
                    if '?' in trojan_data:
                        password, rest = trojan_data.split('?', 1)
                        server = password
                        port = "443"  # 默认端口
                    else:
                        password = trojan_data
                        server = trojan_data
                        port = "443"
                else:
                    # 标准格式：password@server:port?params
                    password, server_part = trojan_data.split('@', 1)
                    if '?' in server_part:
                        server_port, params = server_part.split('?', 1)
                    else:
                        server_port = server_part
                        params = ""
                    
                    if ':' in server_port:
                        server, port = server_port.split(':', 1)
                    else:
                        server = server_port
                        port = "443"  # 默认端口
                
                # 解析查询参数
                if '?' in trojan_data:
                    params = trojan_data.split('?', 1)[1]
                    query_params = parse_qs(params)
                else:
                    query_params = {}
                
                # 提取设置
                settings = {
                    'password': password,
                    'security': query_params.get('security', ['tls'])[0],
                    'type': query_params.get('type', ['tcp'])[0],
                    'host': query_params.get('host', [''])[0],
                    'path': query_params.get('path', ['/'])[0],
                    'sni': query_params.get('sni', [server])[0],
                    'alpn': query_params.get('alpn', ['h2,http/1.1'])[0],
                    'fp': query_params.get('fp', [''])[0],
                    'allowInsecure': query_params.get('allowInsecure', ['0'])[0]
                }
                
                # 创建代理对象
                proxy = Proxy(
                    raw_link=line,
                    proxy_type='trojan',
                    server=server,
                    port=int(port),
                    settings=settings
                )
                
                if self.logger:
                    self.logger.debug(f"Successfully parsed Trojan proxy: {server}:{port}")
                    self.logger.debug(f"Settings: {settings}")
                
                return proxy
                
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"Failed to parse Trojan link with first method: {str(e)}")
                raise
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to parse Trojan link: {str(e)}")
            raise ValueError(f"Invalid trojan link: {str(e)}")