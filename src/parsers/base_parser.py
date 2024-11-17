from typing import List

class BaseParser:
    """基础解析器 - 用于解析订阅内容的格式"""
    
    def parse(self, content: str) -> List[str]:
        """解析内容为代理链接列表"""
        raise NotImplementedError