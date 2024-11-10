from urllib.parse import urlparse, parse_qs, unquote
from .base_protocol_parser import BaseProtocolParser
from ...models.proxy import Proxy
from .protocol_parser_factory import ProtocolParserFactory

@ProtocolParserFactory.register
class VlessParser(BaseProtocolParser):
    @classmethod
    def protocol_prefix(cls) -> str:
        return 'vless://'
    
    def parse(self, line: str) -> Proxy:
        try:
            if self.logger:
                self.logger.debug(f"Parsing VLESS link: {line[:50]}...")
            
            # 移除前缀
            vless_data = line[len(self.protocol_prefix()):]
            
            try:
                # 处理URL编码
                vless_data = unquote(vless_data)
                
                # 解析URL
                if '@' not in vless_data:
                    raise ValueError("Missing server information")
                
                # 标准格式：uuid@server:port?params
                uuid, server_part = vless_data.split('@', 1)
                
                # 处理服务器和端口
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
                query_params = parse_qs(params)
                
                # 提取设置
                settings = {
                    'uuid': uuid,
                    'encryption': query_params.get('encryption', ['none'])[0],
                    'security': query_params.get('security', ['none'])[0],
                    'type': query_params.get('type', ['tcp'])[0],
                    'host': query_params.get('host', [''])[0],
                    'path': query_params.get('path', ['/'])[0],
                    'sni': query_params.get('sni', [server])[0],
                    'alpn': query_params.get('alpn', ['h2,http/1.1'])[0],
                    'fp': query_params.get('fp', [''])[0],
                    'headerType': query_params.get('headerType', ['none'])[0],
                    'flow': query_params.get('flow', [''])[0],
                    'serviceName': query_params.get('serviceName', [''])[0]
                }
                
                # 处理reality配置
                if settings['security'] == 'reality':
                    settings.update({
                        'pbk': query_params.get('pbk', [''])[0],
                        'sid': query_params.get('sid', [''])[0]
                    })
                
                # 创建代理对象
                proxy = Proxy(
                    raw_link=line,
                    proxy_type='vless',
                    server=server,
                    port=int(port),
                    settings=settings
                )
                
                if self.logger:
                    self.logger.debug(f"Successfully parsed VLESS proxy: {server}:{port}")
                    self.logger.debug(f"Settings: {settings}")
                
                return proxy
                
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"Failed to parse VLESS link with first method: {str(e)}")
                raise
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to parse VLESS link: {str(e)}")
            raise ValueError(f"Invalid vless link: {str(e)}") 