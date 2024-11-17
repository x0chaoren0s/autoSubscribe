import base64
from typing import List
from .base_parser import BaseParser
from .line_parser import LineParser

class Base64Parser(BaseParser):
    """Base64解析器 - 用于解析Base64编码的订阅内容"""
    
    def __init__(self):
        self.line_parser = LineParser()
    
    def parse(self, content: str) -> List[str]:
        """解析Base64编码的内容为代理链接列表"""
        try:
            # 添加填充
            padding = 4 - len(content) % 4
            if padding != 4:
                content += '=' * padding
                
            # Base64解码
            decoded = base64.urlsafe_b64decode(content).decode('utf-8')
            
            # 使用行解析器处理解码后的内容
            return self.line_parser.parse(decoded)
            
        except Exception as e:
            raise ValueError(f"Invalid Base64 content: {str(e)}") 