import base64
from typing import List
from .base_parser import BaseParser
from .line_parser import LineParser
from ..models.proxy import Proxy
from ..utils.constants import SUPPORTED_PROTOCOLS

class Base64Parser(BaseParser):
    """Base64编码内容的解析器"""
    
    def __init__(self, logger=None):
        """
        初始化Base64Parser
        
        Args:
            logger: 日志记录器
        """
        super().__init__(logger)
        # 使用LineParser来处理解码后的内容
        self.line_parser = LineParser(logger=logger)
    
    @classmethod
    def can_parse(cls, content: str) -> bool:
        """
        判断内容是否是base64编码
        
        Args:
            content: 要判断的内容
            
        Returns:
            bool: 如果内容是合法的base64编码则返回True
        """
        # 移除可能的空白字符
        content = content.strip()
        
        try:
            # 1. 检查是否符合base64编码规则（长度是4的倍数，只包含合法字符）
            if len(content) % 4 != 0:
                return False
                
            # 2. 检查字符集
            allowed_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
            if not all(c in allowed_chars for c in content):
                return False
            
            # 3. 尝试解码并检查结果
            decoded = base64.b64decode(content).decode('utf-8')
            
            # 检查是否包含代理链接
            has_proxy = any(
                line.strip().startswith(f"{protocol}://")
                for protocol in SUPPORTED_PROTOCOLS
                for line in decoded.splitlines()
                if line.strip()
            )
            
            # 如果直接包含代理链接，返回True
            if has_proxy:
                return True
                
            # 如果不包含代理链接，尝试再次base64解码
            # 这是为了处理双重base64编码的情况
            try:
                double_decoded = base64.b64decode(decoded).decode('utf-8')
                return any(
                    line.strip().startswith(f"{protocol}://")
                    for protocol in SUPPORTED_PROTOCOLS
                    for line in double_decoded.splitlines()
                    if line.strip()
                )
            except:
                return False
            
        except Exception as e:
            if hasattr(cls, 'logger'):
                cls.logger.debug(f"Not base64 content: {str(e)}")
            return False
    
    def parse(self, content: str) -> List[Proxy]:
        """
        解析base64编码的内容
        
        Args:
            content: base64编码的内容
            
        Returns:
            List[Proxy]: 解析出的代理列表
            
        Raises:
            ValueError: 当内容不是有效的base64编码时抛出
        """
        try:
            # 1. 移除空白字符
            content = content.strip()
            
            # 2. Base64解码
            decoded = base64.b64decode(content).decode('utf-8')
            if self.logger:
                self.logger.debug(f"Successfully decoded base64 content, length: {len(decoded)}")
            
            # 检查是否包含代理链接
            has_proxy = any(
                line.strip().startswith(f"{protocol}://")
                for protocol in SUPPORTED_PROTOCOLS
                for line in decoded.splitlines()
                if line.strip()
            )
            
            # 如果不包含代理链接，尝试再次解码
            if not has_proxy:
                try:
                    decoded = base64.b64decode(decoded).decode('utf-8')
                    if self.logger:
                        self.logger.debug("Successfully decoded double base64 content")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Failed to decode double base64: {str(e)}")
            
            # 3. 使用LineParser解析解码后的内容
            proxies = self.line_parser.parse(decoded)
            
            # 4. 清理代理设置
            for proxy in proxies:
                proxy.clean_settings()
            
            return proxies
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to parse base64 content: {str(e)}")
            raise ValueError(f"Failed to parse base64 content: {str(e)}") 