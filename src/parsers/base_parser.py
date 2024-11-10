from abc import ABC, abstractmethod
from typing import List
from ..models.proxy import Proxy

class BaseParser(ABC):
    """代理链接解析器的基类"""
    
    _logger = None  # 类级别的logger
    
    def __init__(self, logger=None):
        self.logger = logger
        self.__class__._logger = logger  # 设置类级别的logger
    
    @abstractmethod
    def parse(self, content: str) -> List[Proxy]:
        """解析内容并返回代理列表"""
        pass
    
    @classmethod
    @abstractmethod
    def can_parse(cls, content: str) -> bool:
        """判断是否可以解析该内容"""
        pass 