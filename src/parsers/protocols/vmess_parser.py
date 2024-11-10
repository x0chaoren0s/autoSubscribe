import json
import base64
from .base_protocol_parser import BaseProtocolParser
from ...models.proxy import Proxy
from .protocol_parser_factory import ProtocolParserFactory

@ProtocolParserFactory.register
class VmessParser(BaseProtocolParser):
    @classmethod
    def protocol_prefix(cls) -> str:
        return 'vmess://'
    
    def parse(self, line: str) -> Proxy:
        try:
            if self.logger:
                self.logger.debug(f"Parsing VMess link: {line[:50]}...")
            
            # 移除前缀
            vmess_data = line[len(self.protocol_prefix()):]
            
            try:
                # 处理非ASCII字符
                vmess_data = vmess_data.encode('utf-8').decode('ascii', errors='ignore')
                decoded = base64.b64decode(vmess_data).decode('utf-8')
                if self.logger:
                    self.logger.debug("Successfully decoded base64 content")
                
                config = json.loads(decoded)
                if self.logger:
                    self.logger.debug(f"Parsed VMess config: {json.dumps(config, indent=2)}")
                
                # 提取必要字段
                server = config.get('add', '')
                port = int(config.get('port', 0))
                settings = {
                    'id': config.get('id', ''),
                    'aid': config.get('aid', 0),
                    'net': config.get('net', ''),
                    'type': config.get('type', ''),
                    'host': config.get('host', ''),
                    'path': config.get('path', ''),
                    'tls': config.get('tls', ''),
                    'sni': config.get('sni', ''),
                    'alpn': config.get('alpn', ''),
                    'fp': config.get('fp', '')
                }
                
                proxy = Proxy(
                    raw_link=line,
                    proxy_type='vmess',
                    server=server,
                    port=port,
                    settings=settings
                )
                
                if self.logger:
                    self.logger.debug(f"Successfully created VMess proxy: {proxy.server}:{proxy.port}")
                
                return proxy
                
            except base64.binascii.Error as e:
                if self.logger:
                    self.logger.error(f"Base64 decode failed: {str(e)}")
                raise
            except json.JSONDecodeError as e:
                if self.logger:
                    self.logger.error(f"JSON decode failed: {str(e)}")
                raise
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to parse VMess link: {str(e)}")
            raise ValueError(f"Invalid vmess link: {str(e)}")