from typing import List, Optional
from .base_parser import BaseParser
from .protocols.protocol_parser_factory import ProtocolParserFactory
from ..models.proxy import Proxy
# 导入协议模块以确保注册
from .protocols import *

class LineParser(BaseParser):
    """按行解析代理链接的解析器"""
    
    _logger = None  # 类级别的logger
    
    def __init__(self, logger=None):
        self.logger = logger
        LineParser._logger = logger  # 设置类级别的logger
    
    @classmethod
    def can_parse(cls, content: str) -> bool:
        """判断内容是否可以用行解析器解析"""
        # 检查每一行，计算有效协议的数量
        valid_count = 0
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):  # 跳过空行和注释行
                continue
                
            # 检查是否是支持的协议
            if any(line.startswith(prefix) for prefix in ProtocolParserFactory._parsers.keys()):
                valid_count += 1
        
        return valid_count > 0

    def parse(self, content: str) -> List[Proxy]:
        """解析内容并返回代理列表"""
        proxies = []
        error_counts = {}  # 记录每种错误的出现次数
        
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):  # 跳过空行和注释行
                continue
                
            try:
                parser = ProtocolParserFactory.create_parser(line)
                proxy = parser.parse(line)
                if proxy:
                    proxies.append(proxy)
                    
            except ValueError as e:
                # 记录错误次数
                error_msg = str(e)
                error_counts[error_msg] = error_counts.get(error_msg, 0) + 1
                
            except Exception as e:
                # 记录错误次数
                error_msg = f"Error parsing line: {str(e)}"
                error_counts[error_msg] = error_counts.get(error_msg, 0) + 1
        
        # 在最后统一输出错误信息
        if error_counts and self.logger:
            for error_msg, count in error_counts.items():
                self.logger.debug(f"Failed to parse {count} links: {error_msg}")
        
        return proxies