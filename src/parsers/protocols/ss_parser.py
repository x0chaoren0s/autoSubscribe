import base64
import re
from urllib.parse import urlparse, parse_qs, unquote
from .base_protocol_parser import BaseProtocolParser
from ...models.proxy import Proxy
from .protocol_parser_factory import ProtocolParserFactory

@ProtocolParserFactory.register
class SSParser(BaseProtocolParser):
    @classmethod
    def protocol_prefix(cls) -> str:
        return 'ss://'
    
    def parse(self, line: str) -> Proxy:
        try:
            if self.logger:
                self.logger.debug(f"Parsing SS link: {line[:50]}...")
            
            # 移除前缀和注释部分
            ss_data = line[len(self.protocol_prefix()):]
            if '#' in ss_data:
                ss_data = ss_data.split('#')[0]
            
            try:
                # 尝试解析新格式 ss://base64(method:password)@server:port
                if '@' in ss_data:
                    userinfo, server_port = ss_data.split('@', 1)
                    try:
                        # 尝试base64解码userinfo部分
                        decoded = base64.b64decode(userinfo).decode('utf-8')
                        method, password = decoded.split(':', 1)
                    except:
                        # 如果解码失败，可能userinfo部分没有base64编码
                        method, password = userinfo.split(':', 1)
                    
                    # 处理server:port部分
                    if ':' in server_port:
                        server, port = server_port.split(':', 1)
                        # 移除可能的查询参数
                        port = port.split('?')[0].split('/')[0]
                    else:
                        server = server_port
                        port = "8388"  # 默认端口
                
                # 尝试解析旧格式 ss://base64(method:password@server:port)
                else:
                    try:
                        decoded = base64.b64decode(ss_data).decode('utf-8')
                        if '@' in decoded:
                            method_pass, server_port = decoded.split('@', 1)
                            method, password = method_pass.split(':', 1)
                            server, port = server_port.split(':', 1)
                        else:
                            raise ValueError("Invalid format")
                    except:
                        raise ValueError("Failed to decode base64 content")
                
                # 清理并验证数据
                server = server.strip()
                port = int(port.strip())
                method = method.strip().lower()
                
                if not server or not method or not password:
                    raise ValueError("Missing required fields")
                
                # 创建代理对象
                proxy = Proxy(
                    raw_link=line,
                    proxy_type='ss',
                    server=server,
                    port=port,
                    settings={
                        'method': method,
                        'password': password
                    }
                )
                
                if self.logger:
                    self.logger.debug(f"Successfully parsed SS proxy: {server}:{port}")
                    self.logger.debug(f"Method: {method}")
                
                return proxy
                
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"Failed to parse SS link with first method: {str(e)}")
                raise
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to parse SS link: {str(e)}")
            raise ValueError(f"Invalid shadowsocks link: {str(e)}")