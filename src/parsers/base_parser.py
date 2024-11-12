from abc import ABC, abstractmethod
from typing import List
from ..models.proxy import Proxy
from ..utils.constants import SUPPORTED_PROTOCOLS

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
    
    def to_glider_urls(self, proxies: List[Proxy]) -> List[str]:
        """转换为Glider URL格式（可选实现）"""
        urls = []
        for proxy in proxies:
            url = proxy.to_glider_url()
            if url:
                urls.append(url)
        return urls