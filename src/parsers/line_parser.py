from typing import List, Optional
from .base_parser import BaseParser
from .protocols.protocol_parser_factory import ProtocolParserFactory
from ..models.proxy import Proxy
from ..utils.constants import SUPPORTED_PROTOCOLS
# 导入协议模块以确保注册
from .protocols import *

class LineParser(BaseParser):
    """按行解析代理链接的解析器"""
    
    def parse(self, content: str) -> List[Proxy]:
        """
        解析内容并返回代理列表
        
        Args:
            content: 要解析的内容
            
        Returns:
            List[Proxy]: 解析出的代理列表
        """
        proxies = []
        error_counts = {}  # 记录每种错误的出现次数
        
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            try:
                parser = ProtocolParserFactory.create_parser(line)
                proxy = parser.parse(line)
                if proxy and proxy.is_valid():
                    # 清理代理设置
                    proxy.clean_settings()
                    proxies.append(proxy)
            except Exception as e:
                # 记录错误次数
                error_msg = f"Error parsing line: {str(e)}"
                error_counts[error_msg] = error_counts.get(error_msg, 0) + 1
        
        # 在最后统一输出错误信息
        if error_counts and self.logger:
            for error_msg, count in error_counts.items():
                self.logger.debug(f"Failed to parse {count} links: {error_msg}")
        
        return proxies
    
    @classmethod
    def can_parse(cls, content: str) -> bool:
        """
        判断是否可以解析该内容
        
        Args:
            content: 要判断的内容
            
        Returns:
            bool: 如果内容包含任何支持的协议前缀则返回True
        """
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 检查是否包含任何支持的协议前缀
            for protocol in SUPPORTED_PROTOCOLS:
                if line.startswith(f"{protocol}://"):
                    return True
        return False